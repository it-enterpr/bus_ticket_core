# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/models/trip_templates.py

from odoo import models, fields, api
from datetime import date, timedelta, datetime

class BusTripTemplate(models.Model):
    _name = 'bus.ticket.trip.template'
    _description = 'Trip Template for recurring trips'
    
    name = fields.Char(string="Template Name", required=True)
    active = fields.Boolean(default=True)
    route_id = fields.Many2one('bus.ticket.route', string='Route', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Default Vehicle')
    driver_id = fields.Many2one('res.partner', string='Default Driver')
    departure_time = fields.Float(string="Departure Time", help="Departure time in hours from midnight (e.g., 14.5 for 14:30).")
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

    def _get_arrival_datetime(self, departure_dt):
        """
        Vypočítá čas příjezdu do cílové destinace na základě nastavení zastávek na lince.
        """
        self.ensure_one()
        if not self.route_id or not self.route_id.stop_line_ids:
            return departure_dt # Není definována linka, vrátíme čas odjezdu

        # Najdeme poslední zastávku podle sekvence
        last_stop = self.route_id.stop_line_ids.sorted('sequence')[-1]
        
        # Vypočítáme celkový offset
        total_offset_hours = last_stop.offset_time
        total_offset_days = last_stop.offset_days
        
        arrival_dt = departure_dt + timedelta(days=total_offset_days, hours=total_offset_hours)
        return arrival_dt

    @api.model
    def _cron_generate_trips(self):
        """
        VYLEPŠENÍ: Generuje budoucí spoje s dynamicky vypočítaným časem příjezdu.
        """
        Trip = self.env['bus.ticket.trip']
        today = date.today()
        # Generujeme spoje na 30 dní dopředu (lze změnit)
        future_date = today + timedelta(days=30)
        
        for template in self.search([('active', '=', True)]):
            start_date = max(today, template.date_from) if template.date_from else today
            end_date = min(future_date, template.date_to) if template.date_to else future_date
            exception_dates = {ex.date for ex in template.exception_date_ids}
            
            # Slovník pro dny v týdnu pro snadnější přístup
            weekdays_map = {
                0: template.monday, 1: template.tuesday, 2: template.wednesday,
                3: template.thursday, 4: template.friday, 5: template.saturday, 6: template.sunday
            }
            
            current_date = start_date
            while current_date <= end_date:
                # Zkontrolujeme, zda se má v daný den v týdnu spoj generovat
                if weekdays_map.get(current_date.weekday()) and current_date not in exception_dates:
                    
                    # Vytvoření plného datetime objektu pro odjezd
                    departure_hour = int(template.departure_time)
                    departure_minute = int((template.departure_time * 60) % 60)
                    departure_dt = datetime.combine(current_date, datetime.min.time()).replace(hour=departure_hour, minute=departure_minute)
                    
                    # Zkontrolujeme, jestli už spoj pro tento den a šablonu neexistuje
                    if not Trip.search_count([('trip_template_id', '=', template.id), ('departure_time', '=', departure_dt)]):
                        
                        # OPRAVA: Dynamický výpočet času příjezdu
                        arrival_dt = template._get_arrival_datetime(departure_dt)

                        Trip.create({
                            'name': f"{template.name} on {current_date.strftime('%Y-%m-%d')}",
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
    _description = 'Exception date for a trip template'
    template_id = fields.Many2one('bus.ticket.trip.template', required=True, ondelete='cascade')
    date = fields.Date(string="Date", required=True)
    reason = fields.Char(string="Reason")