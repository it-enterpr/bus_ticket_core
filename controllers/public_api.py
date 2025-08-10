# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/controllers/public_api.py
import json
from odoo import http
from odoo.http import request, Response
import logging
_logger = logging.getLogger(__name__)

class PublicBusTicketApi(http.Controller):
    # UJISTĚTE SE, ŽE JE ZDE 'GET' A 'auth="public"'
    @http.route('/api/v1/cities', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_cities(self, **kw):
        """Vrátí unikátní seznam měst ze všech zastávek."""
        try:
            # Použijeme read_group pro efektivní získání unikátních měst
            grouped_data = request.env['bus.ticket.stop'].read_group(
                [('city', '!=', False), ('city', '!=', '')], 
                ['city'], 
                ['city'],
                orderby='city'
            )
            # Extrahuje názvy měst ze seskupených dat
            cities = [g['city'] for g in grouped_data]
            
            return Response(
                json.dumps({'cities': cities}), 
                content_type='application/json; charset=utf-8', 
                status=200
            )
        except Exception as e:
            _logger.error(f"API Error in /cities: {e}")
            return Response(
                json.dumps({'error': 'Could not fetch cities.'}), 
                content_type='application/json; charset=utf-8', 
                status=500
            )