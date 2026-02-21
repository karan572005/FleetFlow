# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class FleetFlowDriver(models.Model):
    _name = 'fleetflow.driver'
    _description = 'FleetFlow Driver Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    # ─── PERSONAL INFO ─────────────────────────────────────────────
    name = fields.Char(string='Full Name', required=True, tracking=True)
    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email')
    employee_id = fields.Many2one(
        'hr.employee', string='Linked Employee',
        help='Link to HR employee record if applicable.')

    # ─── LICENSE & COMPLIANCE ──────────────────────────────────────
    license_number = fields.Char(
        string='License Number', required=True, copy=False)
    license_expiry_date = fields.Date(
        string='License Expiry Date', required=True, tracking=True)
    license_categories = fields.Many2many(
        'fleetflow.license.category',
        string='License Categories',
        help='Types of vehicles this driver is licensed to drive (Truck, Van, Bike).',
    )
    license_status = fields.Selection([
        ('valid',    'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired',  'Expired'),
    ], string='License Status', compute='_compute_license_status', store=True)

    # ─── DUTY STATUS ───────────────────────────────────────────────
    status = fields.Selection([
        ('on_duty',   'On Duty'),
        ('off_duty',  'Off Duty'),
        ('suspended', 'Suspended'),
    ], string='Duty Status', default='off_duty', tracking=True)

    # ─── SAFETY & PERFORMANCE ──────────────────────────────────────
    safety_score = fields.Float(
        string='Safety Score', default=100.0,
        help='Score out of 100. Deducted on violations.')
    trips_completed = fields.Integer(
        string='Trips Completed', compute='_compute_trip_stats', store=True)
    trips_total = fields.Integer(
        string='Total Trips Assigned', compute='_compute_trip_stats', store=True)
    completion_rate = fields.Float(
        string='Completion Rate (%)', compute='_compute_trip_stats', store=True)

    # ─── RELATIONS ─────────────────────────────────────────────────
    trip_ids = fields.One2many(
        'fleetflow.trip', 'driver_id', string='Trips')

    # ─── NOTES ─────────────────────────────────────────────────────
    notes = fields.Text(string='Notes / Remarks')

    # ─── COMPUTED: LICENSE STATUS ─────────────────────────────────
    @api.depends('license_expiry_date')
    def _compute_license_status(self):
        today = date.today()
        for driver in self:
            if not driver.license_expiry_date:
                driver.license_status = 'expired'
                continue
            delta = (driver.license_expiry_date - today).days
            if delta < 0:
                driver.license_status = 'expired'
            elif delta <= 30:
                driver.license_status = 'expiring'
            else:
                driver.license_status = 'valid'

    # ─── COMPUTED: TRIP PERFORMANCE ───────────────────────────────
    @api.depends('trip_ids.state')
    def _compute_trip_stats(self):
        for driver in self:
            all_trips = driver.trip_ids.filtered(
                lambda t: t.state not in ('draft', 'cancelled')
            )
            completed = all_trips.filtered(lambda t: t.state == 'completed')
            driver.trips_total = len(all_trips)
            driver.trips_completed = len(completed)
            driver.completion_rate = (
                len(completed) / len(all_trips) * 100
                if all_trips else 0.0
            )

    # ─── PYTHON CONSTRAINT: Block if expired ──────────────────────
    @api.constrains('license_expiry_date')
    def _check_license_expiry(self):
        """Warn if license already expired — blocking happens at trip assignment."""
        pass  # Blocking logic is in fleetflow.trip._check_driver_license

    # ─── SQL CONSTRAINT ───────────────────────────────────────────
    _sql_constraints = [
        ('license_unique', 'UNIQUE(license_number)',
         'License number must be unique!'),
    ]

    # ─── BUTTONS ──────────────────────────────────────────────────
    def action_set_on_duty(self):
        for rec in self:
            rec.status = 'on_duty'

    def action_set_off_duty(self):
        for rec in self:
            rec.status = 'off_duty'

    def action_suspend(self):
        for rec in self:
            rec.status = 'suspended'


class FleetFlowLicenseCategory(models.Model):
    _name = 'fleetflow.license.category'
    _description = 'License Category (Truck / Van / Bike)'

    name = fields.Char(string='Category', required=True)
    vehicle_type = fields.Selection([
        ('truck', 'Truck'),
        ('van',   'Van'),
        ('bike',  'Bike'),
    ], string='Vehicle Type')
