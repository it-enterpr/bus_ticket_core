# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/models/price_models.py

from odoo import models, fields

# ===================================================================
# Model pro Ceny (Price)
# ===================================================================
class BusPrice(models.Model):
    _name = 'bus.ticket.price'
    _description = 'Bus Ticket Pricing'

    # TOTO JE ZPĚTNÉ POLE, které propojuje cenu s konkrétní trasou.
    # Jeho existence je klíčová pro opravu chyby 'KeyError: route_id'.
    route_id = fields.Many2one(
        comodel_name='bus.ticket.route', 
        string="Route", 
        required=True, 
        ondelete='cascade'
    )

    stop_from_id = fields.Many2one('bus.ticket.stop', string="From Stop", required=True)
    stop_to_id = fields.Many2one('bus.ticket.stop', string="To Stop", required=True)
    
    price = fields.Float(string="Price", default=0.0)
    
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        related='route_id.company_id.currency_id',
        store=True # Je dobrým zvykem u related polí přidat store=True pro lepší výkon
    )
