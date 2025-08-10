# -*- coding: utf-8 -*-
# Soubor: bus_ticket_core/models/route_models.py

from odoo import models, fields, api
from itertools import combinations

class BusRoute(models.Model):
    _name = 'bus.ticket.route'
    _description = 'Bus Ticket Route'
    # OPRAVA: Dědíme pouze z mixinů, ne ze sebe sama
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Route Name", required=True, tracking=True, translate=True)
    stop_line_ids = fields.One2many('bus.ticket.way.point', 'route_id', string='Stops (Waypoints)')
    price_ids = fields.One2many('bus.ticket.price', 'route_id', string='Pricing')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # --- INFORMATIVNÍ POLE ---
    start_stop_id = fields.Many2one('bus.ticket.stop', string="Start Stop", compute='_compute_start_end_stops', store=True)
    end_stop_id = fields.Many2one('bus.ticket.stop', string="End Stop", compute='_compute_start_end_stops', store=True)

    @api.depends('stop_line_ids', 'stop_line_ids.sequence')
    def _compute_start_end_stops(self):
        for route in self:
            sorted_stops = route.stop_line_ids.sorted('sequence')
            if sorted_stops:
                route.start_stop_id = sorted_stops[0].stop_id
                route.end_stop_id = sorted_stops[-1].stop_id
            else:
                route.start_stop_id = False
                route.end_stop_id = False
    
    def generate_pricing(self):
        self.ensure_one()
        Price = self.env['bus.ticket.price']
        self.price_ids.unlink()
        stops = self.stop_line_ids.sorted('sequence')
        if len(stops) < 2:
            return

        price_vals = [
            {
                'route_id': self.id,
                'stop_from_id': stop_from.stop_id.id,
                'stop_to_id': stop_to.stop_id.id
            }
            for stop_from, stop_to in combinations(stops, 2)
        ]
        if price_vals:
            Price.create(price_vals)

class BusStop(models.Model):
    _name = 'bus.ticket.stop'
    _description = 'Bus Stop'

    name = fields.Char(string='Stop Name', required=True, translate=True)
    city = fields.Char(string='City', compute='_compute_city', store=True, help="City is automatically extracted from the stop name.")

    @api.depends('name')
    def _compute_city(self):
        for stop in self:
            if stop.name:
                stop.city = stop.name.split(',')[0].strip()
            else:
                stop.city = False
