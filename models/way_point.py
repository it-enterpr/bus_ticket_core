# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/models/way_point.py

from odoo import models, fields, api
from itertools import combinations


# Původní název: class BusRouteStopLine(models.Model):
class BusTicketWayPoint(models.Model):
    _name = 'bus.ticket.way.point'  # <-- NOVÝ NÁZEV
    _description = 'Waypoint on a Route'
    _order = 'sequence,id'

    route_id = fields.Many2one('bus.ticket.route', required=True, ondelete='cascade')

    stop_id = fields.Many2one('bus.ticket.stop', required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    offset_days = fields.Integer(string="Day Offset", default=0)
    offset_time = fields.Float(string="Time")