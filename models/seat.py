# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SeatLayout(models.Model):
    _name = 'bus.ticket.seat.layout'
    _description = 'Bus Seat Layout'
    name = fields.Char(string="Layout Name", required=True)
    total_seats = fields.Integer(string="Total Seats", compute='_compute_total_seats', store=True)
    layout_line_ids = fields.One2many('bus.ticket.seat.layout.line', 'layout_id', string="Layout Lines")
    
    @api.depends('layout_line_ids.seat_count')
    def _compute_total_seats(self):
        for layout in self:
            layout.total_seats = sum(line.seat_count for line in layout.layout_line_ids)

class SeatLayoutLine(models.Model):
    _name = 'bus.ticket.seat.layout.line'
    _description = 'Bus Seat Layout Line'
    _order = 'sequence, id'
    sequence = fields.Integer(default=10)
    layout_id = fields.Many2one('bus.ticket.seat.layout', required=True, ondelete='cascade')
    row_name = fields.Char(string="Row", required=True)
    seat_count = fields.Integer(string="Number of Seats in Row", required=True)

class TripSeat(models.Model):
    _name = 'bus.ticket.trip.seat'
    _description = 'Seat on a specific trip'
    _order = 'row, number'

    trip_id = fields.Many2one('bus.ticket.trip', string='Trip', required=True, ondelete='cascade')
    seat_name = fields.Char(string="Seat Name")
    row = fields.Char(string="Row")
    number = fields.Integer(string="Number")
    state = fields.Selection([('available', 'Available'), ('reserved', 'Reserved'), ('sold', 'Sold')], string='Status', default='available', required=True)
    
    # OPRAVA: Změněno z neexistujícího One2one na One2many a přejmenováno na plurál
    # Odkazujeme na pole 'seat_id' v modelu 'sale.order.line'
    order_line_ids = fields.One2many('sale.order.line', 'seat_id', string="Sale Order Lines")

