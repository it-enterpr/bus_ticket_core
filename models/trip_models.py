# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta, datetime

class BusTrip(models.Model):
    _name = 'bus.ticket.trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bus Trip (Concrete Instance)'
    _order = 'display_group, departure_time desc' # Nové výchozí řazení

    name = fields.Char(string='Trip Name', required=True, tracking=True, readonly=True, default="New Trip")
    route_id = fields.Many2one('bus.ticket.route', 'Route', required=True, tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', tracking=True)
    driver_id = fields.Many2one('res.partner', 'Driver', tracking=True, domain="[('is_company', '=', False)]")
    departure_time = fields.Datetime('Departure Time', required=True, tracking=True)
    arrival_time = fields.Datetime(string='Arrival Time', compute='_compute_arrival_time', store=True, readonly=False)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('in_progress', 'In Progress'), ('done', 'Done'), ('cancelled', 'Cancelled')], 'Status', default='draft', tracking=True)
    
    # Propojení na šablonu
    trip_template_id = fields.Many2one('bus.ticket.trip.template', "Created from Template", ondelete='set null', readonly=True)
    
    seat_ids = fields.One2many('bus.ticket.trip.seat', 'trip_id', 'Seats')
    seat_map_html = fields.Html(string="Seat Map", compute='_compute_seat_map_html', sanitize=False)
    
    # Nová pole pro lepší přehled
    is_sellable = fields.Boolean("Is Sellable", default=True, help="Uncheck to hide this trip from the website.")
    available_seats_count = fields.Integer("Available Seats", compute='_compute_seat_counts', store=True)
    sold_seats_count = fields.Integer("Sold/Reserved Seats", compute='_compute_seat_counts', store=True)
    order_line_ids = fields.One2many(related='seat_ids.order_line_ids', string="Order Lines")
    order_count = fields.Integer("Order Count", compute='_compute_order_count', store=True)
    total_revenue = fields.Monetary("Total Revenue", compute='_compute_total_revenue', store=True)
    company_id = fields.Many2one('res.company', 'Company', related='route_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id')
    
    # Pole pro řazení
    display_group = fields.Selection([('today', 'Today'), ('future', 'Future'), ('past', 'Past')], "Display Group", compute='_compute_display_group', store=True)
    
    start_city = fields.Char(string="From", related='route_id.start_stop_id.city', store=True)
    end_city = fields.Char(string="To", related='route_id.end_stop_id.city', store=True)

    @api.depends('route_id.name', 'departure_time')
    def _compute_trip_name(self):
        for trip in self:
            if trip.route_id and trip.departure_time:
                trip.name = f"{trip.route_id.name} on {trip.departure_time.strftime('%d.%m.%Y')}"
            else:
                trip.name = "New Trip"

    @api.depends('seat_ids', 'seat_ids.state')
    def _compute_seat_map_html(self):
        for trip in self:
            if not trip.seat_ids:
                trip.seat_map_html = "<p>Please generate seats for this trip first.</p>"
                continue
            trip.seat_map_html = self.env['ir.qweb']._render('bus_ticket_core.qweb_seat_map', {'seats': trip.seat_ids})

    @api.depends('departure_time', 'route_id.stop_line_ids.offset_time', 'route_id.stop_line_ids.offset_days')
    def _compute_arrival_time(self):
        for trip in self:
            if trip.departure_time and trip.route_id and trip.route_id.stop_line_ids:
                last_stop = trip.route_id.stop_line_ids.sorted('sequence')[-1]
                trip.arrival_time = trip.departure_time + timedelta(days=last_stop.offset_days, hours=last_stop.offset_time)
            else:
                trip.arrival_time = trip.departure_time

    @api.depends('departure_time')
    def _compute_display_group(self):
        for trip in self:
            if not trip.departure_time: trip.display_group = 'future'; continue
            departure_date = trip.departure_time.date()
            today = fields.Date.today()
            if departure_date > today: trip.display_group = 'future'
            elif departure_date < today: trip.display_group = 'past'
            else: trip.display_group = 'today'

    @api.depends('seat_ids.state')
    def _compute_seat_counts(self):
        for trip in self:
            trip.sold_seats_count = len(trip.seat_ids.filtered(lambda s: s.state in ['sold', 'reserved']))
            trip.available_seats_count = len(trip.seat_ids.filtered(lambda s: s.state == 'available'))

    @api.depends('order_line_ids.price_total', 'order_line_ids.order_id.state')
    def _compute_total_revenue(self):
        for trip in self:
            sold_lines = trip.order_line_ids.filtered(lambda l: l.order_id.state in ['sale', 'done'])
            trip.total_revenue = sum(sold_lines.mapped('price_total'))

    @api.depends('order_line_ids')
    def _compute_order_count(self):
        for trip in self: trip.order_count = len(trip.order_line_ids.mapped('order_id'))
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def generate_seats(self):
        self.ensure_one()
        self.seat_ids.unlink()
        Seat = self.env['bus.ticket.trip.seat']
        layout = self.vehicle_id.seat_layout_id
        if not layout or not layout.total_seats: return
        seat_vals = []
        cols = 5
        current_row, current_col = 0, 0
        for i in range(1, layout.total_seats + 1):
            if current_col == 2: current_col += 1
            seat_vals.append({'trip_id': self.id, 'number': i, 'pos_x': current_col, 'pos_y': current_row})
            current_col += 1
            if current_col >= cols: current_col, current_row = 0, current_row + 1
        if seat_vals: Seat.create(seat_vals)

    @api.model_create_multi
    def create(self, vals_list):
        # Načteme si jména tras dopředu, abychom se neptali databáze v cyklu
        route_ids = [vals.get('route_id') for vals in vals_list if vals.get('route_id')]
        route_names = {r.id: r.name for r in self.env['bus.ticket.route'].browse(route_ids)}

        for vals in vals_list:
            # Sestavíme název a vložíme ho do slovníku hodnot 'vals'
            if vals.get('route_id') and vals.get('departure_time'):
                route_name = route_names.get(vals['route_id'], '')
                departure_dt = fields.Datetime.to_datetime(vals['departure_time'])
                vals['name'] = f"{route_name} on {departure_dt.strftime('%d.%m.%Y')}"
        
        # Zavoláme původní metodu create, ale už s doplněnými názvy
        trips = super(BusTrip, self).create(vals_list)
        
        # Zbytek logiky zůstává
        for trip in trips.filtered(lambda t: t.vehicle_id.seat_layout_id):
            trip.generate_seats()
        return trips

class BusTripTemplate(models.Model):
    _name = 'bus.ticket.trip.template'
    _description = 'Trip Template (Timetable)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Template Name", required=True)
    active = fields.Boolean(default=True)
    route_id = fields.Many2one('bus.ticket.route', string='Route', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Default Vehicle')
    driver_id = fields.Many2one('res.partner', string='Default Driver')
    departure_time = fields.Float(string="Departure Time", help="e.g., 14.5 for 14:30", required=True)
    
    # Dny v týdnu
    monday = fields.Boolean(string="Mon", default=True)
    tuesday = fields.Boolean(string="Tue", default=True)
    wednesday = fields.Boolean(string="Wed", default=True)
    thursday = fields.Boolean(string="Thu", default=True)
    friday = fields.Boolean(string="Fri", default=True)
    saturday = fields.Boolean(string="Sat")
    sunday = fields.Boolean(string="Sun")
    
    date_from = fields.Date(string="Valid From")
    date_to = fields.Date(string="Valid To")
    exception_date_ids = fields.One2many('bus.ticket.trip.template.exception', 'template_id', string="Exception Dates")
    
    company_id = fields.Many2one('res.company', 'Company', related='route_id.company_id', store=True)

    def _get_arrival_datetime(self, departure_dt):
        self.ensure_one()
        if not self.route_id or not self.route_id.stop_line_ids: return departure_dt
        last_stop = self.route_id.stop_line_ids.sorted('sequence')[-1]
        return departure_dt + timedelta(days=last_stop.offset_days, hours=last_stop.offset_time)

    def _cron_generate_trips(self):
        """Metoda volaná CRONem pro generování spojů na X dní dopředu."""
        Trip = self.env['bus.ticket.trip']
        today = date.today()
        # Generujeme na 90 dní dopředu
        future_date = today + timedelta(days=90) 
        
        for template in self.search([('active', '=', True)]):
            start_date = max(today, template.date_from) if template.date_from else today
            end_date = min(future_date, template.date_to) if template.date_to else future_date
            
            exception_dates = {ex.date for ex in template.exception_date_ids}
            weekdays_map = {0: template.monday, 1: template.tuesday, 2: template.wednesday, 3: template.thursday, 4: template.friday, 5: template.saturday, 6: template.sunday}
            
            current_date = start_date
            while current_date <= end_date:
                if weekdays_map.get(current_date.weekday()) and current_date not in exception_dates:
                    departure_hour = int(template.departure_time)
                    departure_minute = int((template.departure_time * 60) % 60)
                    departure_dt = datetime.combine(current_date, datetime.min.time()).replace(hour=departure_hour, minute=departure_minute)
                    
                    # Zkontrolujeme, zda spoj již neexistuje
                    if not Trip.search_count([('trip_template_id', '=', template.id), ('departure_time', '=', departure_dt)]):
                        arrival_dt = template._get_arrival_datetime(departure_dt)
                        Trip.create({
                            'route_id': template.route_id.id,
                            'vehicle_id': template.vehicle_id.id,
                            'driver_id': template.driver_id.id,
                            'departure_time': departure_dt,
                            'arrival_time': arrival_dt,
                            'trip_template_id': template.id,
                        })
                current_date += timedelta(days=1)

class TripTemplateException(models.Model):
    _name = 'bus.ticket.trip.template.exception'
    _description = 'Exception for Trip Template'
    template_id = fields.Many2one('bus.ticket.trip.template', required=True, ondelete='cascade')
    date = fields.Date(string="Date", required=True)
    reason = fields.Char(string="Reason")
