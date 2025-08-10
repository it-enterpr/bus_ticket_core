# -*- coding: utf-8 -*-
import json
from datetime import datetime, time, timedelta
from odoo import http, fields
from odoo.http import request, Response
import logging
_logger = logging.getLogger(__name__)

# --- Správná ověřovací funkce podle JMÉNA klíče ---

def require_api_key(func):
    """Decorator to require a valid API key for an endpoint."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Získání klíče z hlavičky HTTP požadavku
        api_key = request.httprequest.headers.get('api-key')
        
        # Získání uloženého klíče z nastavení Odoo
        stored_key = request.env['ir.config_parameter'].sudo().get_param('bus_ticket_core.api_key')

        # Ověření, zda klíče existují a shodují se
        if not api_key or not stored_key or api_key != stored_key:
            # Pokud ne, vrátíme chybu 401 Unauthorized
            error_response = '{"error": "Unauthorized", "message": "A valid API key is required."}'
            return Response(error_response, status=401, mimetype='application/json')
            
        # Pokud je vše v pořádku, pokračujeme k původní funkci
        return func(self, *args, **kwargs)
    return wrapper

class BusTicketApiController(http.Controller):

    # Použití dekorátoru pro zabezpečení endpointu
    @route('/api/stops', type='json', auth='public', methods=['GET'], cors='*')
    @require_api_key
    def get_stops(self, **kw):
        """
        Returns a list of all bus stops.
        Requires a valid 'api-key' in the request headers.
        """
        stops_data = request.env['bus.ticket.stop'].search_read([], ['id', 'name', 'city'])
        return stops_data


def _authenticate_by_description():
    """Ověří požadavek podle JMÉNA (popisku) API klíče v hlavičce."""
    key_description = request.httprequest.headers.get('X-API-Key')
    if not key_description:
        _logger.warning("API Authentication: Failed - Missing 'X-API-Key' header.")
        return False, "Missing API Key in 'X-API-Key' header."
    
    key_record = request.env['res.users.apikeys'].sudo().search([('name', '=', key_description)], limit=1)
    
    if not key_record:
        _logger.warning(f"API Authentication: Failed - No key found with name '{key_description}'.")
        return False, "Invalid API Key."
        
    _logger.info(f"API Authentication: Success - Found key for user '{key_record.user_id.name}'.")
    return key_record.user_id, None

def _get_trip_data(trip):
    """Naformátuje data o spoji pro API odpověď."""
    return {
        'id': trip.id, 'name': trip.name,
        'route': trip.route_id.name if trip.route_id else None,
        'departure_time': trip.departure_time.strftime('%Y-%m-%d %H:%M:%S') if trip.departure_time else None,
        'arrival_time': trip.arrival_time.strftime('%Y-%m-%d %H:%M:%S') if trip.arrival_time else None,
        'available_seats': trip.available_seats_count,
        'vehicle': { 'name': trip.vehicle_id.name, 'license_plate': trip.vehicle_id.license_plate },
        'driver': { 'name': trip.driver_id.name }
    }

class MainBusTicketApi(http.Controller):

    @http.route('/api/v1/trips/search', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    def search_trips(self, **kw):
        """Vylepšené vyhledávání spojů."""
        user, error_msg = _authenticate_by_description()
        if not user:
            return {'error': {'code': 401, 'message': error_msg}}

        params = request.get_json_data().get('params', {})
        from_city, to_city, departure_date_str = params.get('from_city'), params.get('to_city'), params.get('departure_date')

        if not all([from_city, to_city, departure_date_str]):
            return {'error': {'code': 400, 'message': 'Missing parameters'}}

        try:
            target_date = datetime.strptime(departure_date_str, '%Y-%m-%d').date()
            Price = request.env['bus.ticket.price'].sudo()
            valid_prices = Price.search([('stop_from_id.city', 'ilike', from_city), ('stop_to_id.city', 'ilike', to_city)])
            if not valid_prices: return {'trips': []}

            valid_route_ids = valid_prices.mapped('route_id').ids
            price_map = {price.route_id.id: price.price for price in valid_prices}
            self._ensure_trips_exist_for_date(target_date, valid_route_ids)
            
            start_date, end_date = target_date - timedelta(days=1), target_date + timedelta(days=2)
            domain = [
                ('state', 'in', ['confirmed', 'in_progress', 'draft']), ('is_sellable', '=', True),
                ('departure_time', '>=', datetime.combine(start_date, time.min)),
                ('departure_time', '<=', datetime.combine(end_date, time.max)),
                ('route_id', 'in', valid_route_ids),
            ]
            found_trips = request.env['bus.ticket.trip'].sudo().search(domain, order='departure_time asc')
            
            response_trips = []
            for trip in found_trips:
                trip_data = _get_trip_data(trip)
                trip_data['price'] = {'czk': price_map.get(trip.route_id.id, 0.0)}
                trip_data['is_target_date'] = (trip.departure_time.date() == target_date)
                response_trips.append(trip_data)
            return {'trips': response_trips}
        except Exception as e:
            _logger.error(f"API Error in /trips/search: {e}", exc_info=True)
            return {'error': {'code': 500, 'message': 'Internal Server Error'}}

    def _ensure_trips_exist_for_date(self, target_date, route_ids):
        """Zkontroluje a případně vytvoří spoje ze šablon."""
        Template = request.env['bus.ticket.trip.template'].sudo()
        Trip = request.env['bus.ticket.trip'].sudo()
        templates_to_check = Template.search([('active', '=', True), ('route_id', 'in', route_ids)])

        for template in templates_to_check:
            day_of_week = target_date.weekday()
            weekdays_map = {0: template.monday, 1: template.tuesday, 2: template.wednesday, 3: template.thursday, 4: template.friday, 5: template.saturday, 6: template.sunday}
            
            is_valid_day = weekdays_map.get(day_of_week, False)
            is_in_date_range = (not template.date_from or template.date_from <= target_date) and \
                               (not template.date_to or template.date_to >= target_date)
            is_exception = request.env['bus.ticket.trip.template.exception'].sudo().search_count([
                ('template_id', '=', template.id), ('date', '=', target_date)
            ]) > 0

            if is_valid_day and is_in_date_range and not is_exception:
                departure_hour = int(template.departure_time)
                departure_minute = int((template.departure_time * 60) % 60)
                departure_dt = datetime.combine(target_date, datetime.min.time()).replace(hour=departure_hour, minute=departure_minute)

                if not Trip.search_count([('trip_template_id', '=', template.id), ('departure_time', '=', departure_dt)]):
                    arrival_dt = template._get_arrival_datetime(departure_dt)
                    Trip.create({
                        'route_id': template.route_id.id,
                        'vehicle_id': template.vehicle_id.id,
                        'driver_id': template.driver_id.id,
                        'departure_time': departure_dt,
                        'arrival_time': arrival_dt,
                        'trip_template_id': template.id,
                        'state': 'confirmed'
                    })

    @http.route('/api/v1/trip/<int:trip_id>/seats', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    def get_trip_seats(self, trip_id, **kw):
        """Vrátí seznam sedadel pro daný spoj."""
        user, error_msg = _authenticate_by_description()
        if not user:
            return Response(json.dumps({'error': error_msg}), status=401)
        
        trip = request.env['bus.ticket.trip'].sudo().browse(trip_id)
        if not trip.exists(): return Response(json.dumps({'error': 'Trip not found'}), status=404)

        seats_data = [{'id': s.id, 'name': s.name, 'number': s.number, 'state': s.state, 'pos_x': s.pos_x, 'pos_y': s.pos_y} for s in trip.seat_ids]
        response_data = {
            'seats': seats_data,
            'layout': {
                'type': trip.vehicle_id.seat_layout_id.layout_type if trip.vehicle_id.seat_layout_id else 'other',
                'max_x': max((s['pos_x'] for s in seats_data), default=0),
                'max_y': max((s['pos_y'] for s in seats_data), default=0),
            }
        }
        return Response(json.dumps(response_data), content_type='application/json; charset=utf-8', status=200)
