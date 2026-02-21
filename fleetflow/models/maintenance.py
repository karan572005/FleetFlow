# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FleetFlowMaintenance(models.Model):
    _name = 'fleetflow.maintenance'
    _description = 'FleetFlow Maintenance & Service Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Service Description',
        required=True,
        help='e.g., Oil Change, Tyre Replacement, Engine Repair',
    )
    vehicle_id = fields.Many2one(
        'fleetflow.vehicle',
        string='Vehicle',
        required=True,
        tracking=True,
        ondelete='cascade',
    )
    maintenance_type = fields.Selection([
        ('preventive',  'Preventive'),
        ('corrective',  'Corrective / Repair'),
        ('inspection',  'Inspection'),
        ('tyre',        'Tyre Change'),
        ('oil_change',  'Oil Change'),
        ('other',       'Other'),
    ], string='Service Type', required=True, default='preventive')

    date = fields.Date(
        string='Service Date',
        required=True,
        default=fields.Date.today,
    )
    date_completed = fields.Date(string='Completion Date')
    cost = fields.Float(string='Cost (₹)', default=0.0)
    odometer_at_service = fields.Float(string='Odometer at Service (km)')
    vendor = fields.Char(string='Service Vendor / Garage')
    notes = fields.Text(string='Technician Notes')

    state = fields.Selection([
        ('open',      'In Progress'),
        ('done',      'Completed'),
    ], string='Status', default='open', tracking=True)

    # ─── KEY AUTO-LOGIC ────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        """
        AUTO-LOGIC (FleetFlow Spec §3.5):
        When a maintenance log is created, automatically set
        vehicle status to 'In Shop' — removing it from the
        Dispatcher's vehicle selection pool.
        """
        records = super().create(vals_list)
        for record in records:
            if record.vehicle_id:
                record.vehicle_id.state = 'in_shop'
                record.vehicle_id.message_post(
                    body=(
                        f"🔧 Vehicle sent to shop: {record.name} "
                        f"({record.get_maintenance_type_label()})"
                    ),
                    message_type='notification',
                )
        return records

    def get_maintenance_type_label(self):
        """Helper to get human-readable maintenance type."""
        selection = dict(self._fields['maintenance_type'].selection)
        return selection.get(self.maintenance_type, self.maintenance_type)

    # ─── COMPLETE SERVICE ──────────────────────────────────────────
    def action_complete(self):
        """
        Mark service as done → restore vehicle to 'Available'.
        """
        for record in self:
            record.state = 'done'
            record.date_completed = fields.Date.today()
            # Only restore if no other open maintenance exists
            other_open = self.search([
                ('vehicle_id', '=', record.vehicle_id.id),
                ('state', '=', 'open'),
                ('id', '!=', record.id),
            ])
            if not other_open:
                record.vehicle_id.state = 'available'
                record.vehicle_id.message_post(
                    body="✅ Maintenance completed. Vehicle is now Available.",
                    message_type='notification',
                )
