# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date


class FleetFlowTrip(models.Model):
    _name = 'fleetflow.trip'
    _description = 'FleetFlow Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_planned desc'

    # ─── IDENTIFICATION ────────────────────────────────────────────
    name = fields.Char(
        string='Trip Reference',
        readonly=True,
        copy=False,
        default='New',
    )

    # ─── CORE FIELDS ───────────────────────────────────────────────
    vehicle_id = fields.Many2one(
        'fleetflow.vehicle',
        string='Vehicle',
        required=True,
        tracking=True,
        domain="[('state','=','available')]",
        help='Only Available vehicles are shown here.',
    )
    driver_id = fields.Many2one(
        'fleetflow.driver',
        string='Driver',
        required=True,
        tracking=True,
        domain="[('status','=','on_duty'),('license_status','!=','expired')]",
        help='Only On-Duty drivers with valid licenses are shown.',
    )

    # ─── ROUTE ─────────────────────────────────────────────────────
    origin = fields.Char(string='Origin', required=True)
    destination = fields.Char(string='Destination', required=True)
    date_planned = fields.Date(
        string='Planned Date', required=True, default=fields.Date.today)
    date_completed = fields.Date(string='Completion Date')

    # ─── CARGO ─────────────────────────────────────────────────────
    cargo_description = fields.Char(string='Cargo Description')
    cargo_weight = fields.Float(
        string='Cargo Weight (kg)',
        required=True,
        help='Must not exceed the vehicle max load capacity.',
    )
    distance_km = fields.Float(string='Distance (km)')
    odometer_start = fields.Float(string='Odometer Start (km)')
    odometer_end = fields.Float(string='Odometer End (km)')

    # ─── FINANCIALS ────────────────────────────────────────────────
    revenue = fields.Float(string='Trip Revenue (₹)', default=0.0)

    # ─── LIFECYCLE STATE ───────────────────────────────────────────
    state = fields.Selection([
        ('draft',      'Draft'),
        ('dispatched', 'Dispatched'),
        ('completed',  'Completed'),
        ('cancelled',  'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    # ─── DISPLAY HELPERS ───────────────────────────────────────────
    vehicle_capacity = fields.Float(
        string='Vehicle Max Capacity',
        related='vehicle_id.max_load_capacity',
        readonly=True,
    )
    capacity_warning = fields.Boolean(
        string='Capacity Exceeded',
        compute='_compute_capacity_warning',
        store=True
    )

    # ─── SEQUENCE ON CREATE ────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fleetflow.trip') or 'New'
        return super().create(vals_list)

    # ─── COMPUTED ──────────────────────────────────────────────────
    @api.depends('cargo_weight', 'vehicle_id.max_load_capacity')
    def _compute_capacity_warning(self):
        for trip in self:
            trip.capacity_warning = (
                trip.vehicle_id
                and trip.cargo_weight > trip.vehicle_id.max_load_capacity
            )

    @api.onchange('odometer_start', 'odometer_end')
    def _onchange_odometer(self):
        if self.odometer_start and self.odometer_end:
            self.distance_km = self.odometer_end - self.odometer_start

    # ─── CORE VALIDATION: Cargo Weight ─────────────────────────────
    @api.constrains('cargo_weight', 'vehicle_id')
    def _check_cargo_weight(self):
        """
        RULE: Prevent trip creation if CargoWeight > MaxCapacity.
        This is the #1 business rule from the FleetFlow spec.
        """
        for trip in self:
            if trip.vehicle_id and trip.cargo_weight > trip.vehicle_id.max_load_capacity:
                raise ValidationError(
                    f"❌ Cargo Weight Exceeded!\n\n"
                    f"Vehicle: {trip.vehicle_id.name}\n"
                    f"Max Capacity: {trip.vehicle_id.max_load_capacity} kg\n"
                    f"Your Cargo: {trip.cargo_weight} kg\n\n"
                    f"Please reduce cargo weight or select a higher-capacity vehicle."
                )

    # ─── VALIDATION: Driver License ────────────────────────────────
    @api.constrains('driver_id', 'vehicle_id')
    def _check_driver_license(self):
        """
        RULE: Block trip if driver license is expired.
        RULE: Block trip if driver has no license for this vehicle type.
        """
        for trip in self:
            if not trip.driver_id:
                continue
            # Block expired license
            if trip.driver_id.license_status == 'expired':
                raise ValidationError(
                    f"❌ License Expired!\n\n"
                    f"Driver {trip.driver_id.name}'s license expired on "
                    f"{trip.driver_id.license_expiry_date}.\n"
                    f"Please renew the license before assigning trips."
                )
            # Check vehicle category
            if trip.vehicle_id and trip.driver_id.license_categories:
                allowed_types = trip.driver_id.license_categories.mapped(
                    'vehicle_type')
                if trip.vehicle_id.vehicle_type not in allowed_types:
                    raise ValidationError(
                        f"❌ License Category Mismatch!\n\n"
                        f"Driver {trip.driver_id.name} is not licensed to "
                        f"drive a {trip.vehicle_id.vehicle_type.capitalize()}.\n"
                        f"Allowed categories: {', '.join(allowed_types)}"
                    )

    # ─── WORKFLOW BUTTONS ──────────────────────────────────────────
    def action_dispatch(self):
        """
        DRAFT → DISPATCHED
        Updates Vehicle and Driver status to 'On Trip' / 'On Duty'.
        """
        for trip in self:
            if trip.state != 'draft':
                raise UserError('Only Draft trips can be dispatched.')
            # Re-check vehicle still available
            if trip.vehicle_id.state != 'available':
                raise UserError(
                    f"Vehicle {trip.vehicle_id.name} is no longer available "
                    f"(current status: {trip.vehicle_id.state})."
                )
            trip.vehicle_id.state = 'on_trip'
            trip.driver_id.status = 'on_duty'
            trip.state = 'dispatched'
            trip.message_post(
                body=f"🚛 Trip dispatched: {trip.origin} → {trip.destination}",
                message_type='notification',
            )

    def action_complete(self):
        """
        DISPATCHED → COMPLETED
        Restores Vehicle and Driver to 'Available'.
        Updates odometer and distance.
        """
        for trip in self:
            if trip.state != 'dispatched':
                raise UserError('Only Dispatched trips can be completed.')
            # Update odometer on vehicle
            if trip.odometer_end:
                trip.vehicle_id.odometer = trip.odometer_end
                if trip.odometer_start:
                    trip.distance_km = trip.odometer_end - trip.odometer_start

            trip.vehicle_id.state = 'available'
            trip.driver_id.status = 'off_duty'
            trip.state = 'completed'
            trip.date_completed = date.today()
            trip.message_post(
                body=f"✅ Trip completed. Distance: {trip.distance_km:.1f} km",
                message_type='notification',
            )

    def action_cancel(self):
        """
        ANY → CANCELLED
        Restores Vehicle/Driver if they were on this trip.
        """
        for trip in self:
            if trip.state == 'completed':
                raise UserError('Completed trips cannot be cancelled.')
            if trip.state == 'dispatched':
                # Restore statuses
                trip.vehicle_id.state = 'available'
                trip.driver_id.status = 'off_duty'
            trip.state = 'cancelled'
            trip.message_post(
                body="🚫 Trip cancelled.",
                message_type='notification',
            )

    def action_reset_to_draft(self):
        """CANCELLED → DRAFT (re-open)"""
        for trip in self:
            if trip.state != 'cancelled':
                raise UserError('Only Cancelled trips can be reset to Draft.')
            trip.state = 'draft'
