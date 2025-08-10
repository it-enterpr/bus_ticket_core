# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/controllers/order_api.py
import json
from datetime import datetime
from odoo import http
from odoo.http import request, Response
import logging

_logger = logging.getLogger(__name__)

# Pomocná funkce pro ověření klíče
def _authenticate_by_description():
    key_description = request.httprequest.headers.get('X-API-Key')
    if not key_description:
        return False, "Missing API Key (description) in 'X-API-Key' header."
    
    key_record = request.env['res.users.apikeys'].sudo().search([('name', '=', key_description)], limit=1)
    if not key_record:
        return False, "Invalid API Key (description)."
    
    # Můžeme přidat i kontrolu expirace, pokud ji budete používat
    # if key_record.expire_date and key_record.expire_date < datetime.now().date():
    #     return False, "This API Key is expired."
        
    return key_record.user_id, None


class OrderBusTicketApi(http.Controller):
    @http.route('/api/v1/order/create', type='http', auth='none', methods=['POST'], csrf=False )
    def create_order(self, **kw):
        """
        Vytvoří novou cenovou nabídku (Sale Order) pro vybraná sedadla.
        Ověřuje pomocí popisku API klíče v hlavičce X-API-Key.
        Očekává JSON s: {trip_id, seat_ids, customer_info: {name, email, phone}}
        """
        user, error_msg = _authenticate_by_description()
        if not user:
            return Response(json.dumps({'error': error_msg}), content_type='application/json; charset=utf-8', status=401)

        try:
            # 1. Zpracování vstupních dat
            data = json.loads(request.httprequest.data)
            trip_id = data.get('trip_id')
            seat_ids = data.get('seat_ids')
            customer_info = data.get('customer_info')

            if not all([trip_id, seat_ids, customer_info]):
                return Response(json.dumps({'error': 'Missing required data (trip_id, seat_ids, customer_info).'}), status=400)

            env = request.env(user=user.id)
            
            # 2. Kontrola dostupnosti sedadel
            seats = env['bus.ticket.trip.seat'].browse(seat_ids)
            if not seats:
                 return Response(json.dumps({'error': 'Invalid seat IDs provided.'}), status=400)
            if any(s.state != 'available' for s in seats):
                return Response(json.dumps({'error': 'One or more selected seats are no longer available.'}), status=409)
            
            # 3. Nalezení nebo vytvoření zákazníka (res.partner)
            partner = env['res.partner'].search([('email', '=', customer_info.get('email'))], limit=1)
            if not partner:
                partner = env['res.partner'].create({
                    'name': customer_info.get('name'),
                    'email': customer_info.get('email'),
                    'phone': customer_info.get('phone'),
                })
            
            # 4. Vytvoření cenové nabídky (sale.order)
            ticket_product = env.ref('bus_ticket_core.product_product_bus_ticket')
            trip = env['bus.ticket.trip'].browse(trip_id)
            price = ticket_product.list_price

            order = env['sale.order'].create({
                'partner_id': partner.id,
                'order_line': [
                    (0, 0, {
                        'product_id': ticket_product.id,
                        'name': f"Ticket: {trip.name or ''} - Seat {seat.name or seat.number}",
                        'price_unit': price,
                        'trip_id': trip.id,
                        'seat_id': seat.id,
                    }) for seat in seats
                ]
            })

            # 5. Okamžitá rezervace sedadel
            seats.write({'state': 'reserved'})
            
            # 6. Vrácení skutečných dat o objednávce
            response_data = {
                'order': {
                    'id': order.id,
                    'name': order.name,
                    'amount_total': order.amount_total,
                    'currency': order.currency_id.name,
                }
            }
            return Response(json.dumps(response_data), content_type='application/json; charset=utf-8', status=200)

        except Exception as e:
            _logger.error(f"API Error in /order/create for user {user.login}: {e}")
            return Response(json.dumps({'error': 'An internal error occurred while creating the order.'}), content_type='application/json; charset=utf-8', status=500)