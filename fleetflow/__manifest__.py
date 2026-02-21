# -*- coding: utf-8 -*-
{
    'name': 'FleetFlow — Fleet & Logistics Management',
    'version': '18.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Modular fleet lifecycle, trip dispatching, driver safety & financial tracking',
    'description': """
FleetFlow
=========
A modular fleet & logistics management system built on Odoo 18.

Features:
- Vehicle Registry with lifecycle management
- Trip Dispatcher with cargo validation rules
- Maintenance & Service Logs (auto In-Shop logic)
- Driver Safety & Compliance profiles
- Fuel & Expense tracking per vehicle
- Operational Analytics & Financial Reports
- Role-based access control (Manager / Dispatcher / Safety / Finance)
    """,
    'author': 'FleetFlow Team — Odoo × Gujarat Hackathon 2026',
    'depends': ['base', 'mail', 'hr', 'web'],
    'data': [
        'security/fleetflow_groups.xml',
        'security/ir.model.access.csv',
        'data/fleetflow_sequence.xml',
        'views/vehicle_views.xml',
        'views/driver_views.xml',
        'views/trip_views.xml',
        'views/maintenance_views.xml',
        'views/expense_views.xml',
        'views/analytics_views.xml',
        'views/dashboard_views.xml',
        'views/config_views.xml',
        'views/menu_views.xml',
        'data/demo_data.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
    'fleetflow/static/src/css/fleetflow.css',
    'fleetflow/static/src/js/fleetflow_dashboard.js',
],
        'web.assets_backend_lazy': [
            'fleetflow/static/src/xml/fleetflow_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
}
