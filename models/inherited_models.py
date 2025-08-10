# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/models/inherited_models.py

# -*- coding: utf-8 -*-
from odoo import models, fields

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    seat_layout_id = fields.Many2one('bus.ticket.seat.layout', string="Seat Layout")
    seat_layout_total_seats = fields.Integer(related='seat_layout_id.total_seats', string="Total Seats", readonly=True)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    seat_id = fields.Many2one('bus.ticket.trip.seat', string="Reserved Seat")
    trip_id = fields.Many2one('bus.ticket.trip', string="Trip", ondelete='set null')

# soubor: bus_ticket_core/models/inherited_models.py

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        # OPRAVA: Použijeme přímé volání super() bez argumentů
        res = super().action_confirm()

        # Naše vlastní logika zůstává stejná
        for order in self:
            ticket_lines = order.order_line.filtered(lambda line: line.seat_id)
            if ticket_lines:
                seats_to_update = ticket_lines.mapped('seat_id')
                seats_to_update.write({'state': 'sold'})
        
        return res
