# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    """
    Inherits res.config.settings to add settings for the Bus Ticket API.
    """
    _inherit = 'res.config.settings'

    # Pole pro API klíč, které se ukládá jako systémový parametr
    api_key = fields.Char(
        string='API Secret Key',
        config_parameter='bus_ticket_core.api_key',
        help="The secret key required for external applications to access the API."
    )
