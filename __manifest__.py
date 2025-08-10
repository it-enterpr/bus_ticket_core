# -*- coding: utf-8 -*-
# soubor: bus_ticket_core/__manifest__.py

{
    'name': "Bus Tickets - Core",
    'version': '18.0.9.1.0',
    'summary': "Core models and logic for the Bus Ticket System.",
    'author': "BUS-Tickets.info & IT Enterprise Solutions s.r.o.",
    'website': "https://bus-ticket.info",
    'category': 'Services/Travel',
    'depends': ['base','web', 'mail', 'fleet', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/cron_jobs.xml',
        'views/views.xml',
    ],
    "application": False,  # core není samostatná aplikace
    "installable": True,
    "auto_install": False,
    'icon': 'bus_ticket_core/static/description/icon.svg',
}