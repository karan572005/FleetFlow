# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FleetFlowVehicle(models.Model):
    _name = 'fleetflow.vehicle'
    _description = 'FleetFlow Vehicle Registry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    # ─── BASIC INFO ────────────────────────────────────────────────
    name = fields.Char(
        string='Vehicle Name / Model',
        required=True,
        tracking=True,
    )
    license_plate = fields.Char(
        string='License Plate',
        required=True,
        copy=False,
        tracking=True,
    )
    vehicle_type = fields.Selection([
        ('truck', 'Truck'),
        ('van',   'Van'),
        ('bike',  'Bike'),
    ], string='Vehicle Type', required=True, default='van', tracking=True)

    # ─── CAPACITY & ODOMETER ───────────────────────────────────────
    max_load_capacity = fields.Float(
        string='Max Load Capacity (kg)',
        required=True,
        help='Maximum cargo weight this vehicle can carry in kilograms.',
    )
    odometer = fields.Float(
        string='Current Odometer (km)',
        tracking=True,
    )
    acquisition_cost = fields.Float(
        string='Acquisition Cost (₹)',
        help='Purchase or lease cost used for ROI calculation.',
    )
    region = fields.Char(string='Region', default='Gujarat')

    # ─── STATUS ────────────────────────────────────────────────────
    state = fields.Selection([
        ('available', 'Available'),
        ('on_trip',   'On Trip'),
        ('in_shop',   'In Shop'),
        ('retired',   'Retired'),
    ], string='Status', default='available', tracking=True, copy=False)

    active = fields.Boolean(default=True)

    # ─── RELATIONS ────────────────────────────────────────────────
    trip_ids = fields.One2many(
        'fleetflow.trip', 'vehicle_id', string='Trips')
    maintenance_ids = fields.One2many(
        'fleetflow.maintenance', 'vehicle_id', string='Maintenance Logs')
    expense_ids = fields.One2many(
        'fleetflow.expense', 'vehicle_id', string='Fuel & Expenses')

    # ─── COMPUTED FINANCIALS ───────────────────────────────────────
    total_fuel_cost = fields.Float(
        string='Total Fuel Cost (₹)',
        compute='_compute_total_costs', store=True)
    total_maintenance_cost = fields.Float(
        string='Total Maintenance Cost (₹)',
        compute='_compute_total_costs', store=True)
    total_operational_cost = fields.Float(
        string='Total Operational Cost (₹)',
        compute='_compute_total_costs', store=True,
        help='Fuel Cost + Maintenance Cost')
    total_revenue = fields.Float(
        string='Total Revenue (₹)',
        compute='_compute_total_costs', store=True)
    vehicle_roi = fields.Float(
        string='Vehicle ROI (%)',
        compute='_compute_roi', store=True,
        help='(Revenue - Operational Cost) / Acquisition Cost × 100')
    cost_per_km = fields.Float(
        string='Cost per KM (₹/km)',
        compute='_compute_cost_per_km', store=True)
    total_km_driven = fields.Float(
        string='Total KM Driven',
        compute='_compute_total_km', store=True)
    fuel_efficiency = fields.Float(
        string='Fuel Efficiency (km/L)',
        compute='_compute_fuel_efficiency', store=True)

    # ─── TRIP COUNTS ───────────────────────────────────────────────
    trip_count = fields.Integer(
        string='Total Trips', compute='_compute_trip_count')
    maintenance_count = fields.Integer(
        string='Maintenance Count', compute='_compute_maintenance_count')

    # ─── COMPUTED METHODS ──────────────────────────────────────────
    @api.depends('expense_ids.cost', 'expense_ids.expense_type',
                 'maintenance_ids.cost', 'trip_ids.revenue',
                 'trip_ids.state')
    def _compute_total_costs(self):
        for vehicle in self:
            fuel = sum(
                e.cost for e in vehicle.expense_ids
                if e.expense_type == 'fuel'
            )
            maintenance = sum(m.cost for m in vehicle.maintenance_ids)
            revenue = sum(
                t.revenue for t in vehicle.trip_ids
                if t.state == 'completed'
            )
            vehicle.total_fuel_cost = fuel
            vehicle.total_maintenance_cost = maintenance
            vehicle.total_operational_cost = fuel + maintenance
            vehicle.total_revenue = revenue

    @api.depends('total_revenue', 'total_operational_cost', 'acquisition_cost')
    def _compute_roi(self):
        for vehicle in self:
            if vehicle.acquisition_cost:
                vehicle.vehicle_roi = (
                    (vehicle.total_revenue - vehicle.total_operational_cost)
                    / vehicle.acquisition_cost * 100
                )
            else:
                vehicle.vehicle_roi = 0.0

    @api.depends('trip_ids.distance_km', 'trip_ids.state')
    def _compute_total_km(self):
        for vehicle in self:
            vehicle.total_km_driven = sum(
                t.distance_km for t in vehicle.trip_ids
                if t.state == 'completed'
            )

    @api.depends('total_operational_cost', 'total_km_driven')
    def _compute_cost_per_km(self):
        for vehicle in self:
            if vehicle.total_km_driven:
                vehicle.cost_per_km = (
                    vehicle.total_operational_cost / vehicle.total_km_driven
                )
            else:
                vehicle.cost_per_km = 0.0

    @api.depends('expense_ids.liters', 'total_km_driven')
    def _compute_fuel_efficiency(self):
        for vehicle in self:
            total_liters = sum(
                e.liters for e in vehicle.expense_ids
                if e.expense_type == 'fuel' and e.liters
            )
            if total_liters:
                vehicle.fuel_efficiency = vehicle.total_km_driven / total_liters
            else:
                vehicle.fuel_efficiency = 0.0

    @api.depends('trip_ids')
    def _compute_trip_count(self):
        for vehicle in self:
            vehicle.trip_count = len(vehicle.trip_ids)

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for vehicle in self:
            vehicle.maintenance_count = len(vehicle.maintenance_ids)

    # ─── CONSTRAINTS ───────────────────────────────────────────────
    _sql_constraints = [
        ('license_plate_unique', 'UNIQUE(license_plate)',
         'License plate must be unique across all vehicles!'),
        ('max_capacity_positive', 'CHECK(max_load_capacity > 0)',
         'Max load capacity must be greater than 0 kg!'),
    ]

    # ─── BUTTONS / ACTIONS ─────────────────────────────────────────
    def action_set_available(self):
        for rec in self:
            rec.state = 'available'

    def action_set_retired(self):
        for rec in self:
            rec.state = 'retired'

    def action_view_trips(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Trips — {self.name}',
            'res_model': 'fleetflow.trip',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    def action_view_maintenance(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Maintenance — {self.name}',
            'res_model': 'fleetflow.maintenance',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }
