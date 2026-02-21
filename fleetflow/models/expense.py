# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FleetFlowExpense(models.Model):
    _name = 'fleetflow.expense'
    _description = 'FleetFlow Fuel & Expense Log'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(
        string='Description',
        required=True,
        default='Fuel',
    )
    vehicle_id = fields.Many2one(
        'fleetflow.vehicle',
        string='Vehicle',
        required=True,
        ondelete='cascade',
    )
    trip_id = fields.Many2one(
        'fleetflow.trip',
        string='Related Trip',
        domain="[('vehicle_id','=',vehicle_id)]",
    )
    expense_type = fields.Selection([
        ('fuel',   'Fuel'),
        ('toll',   'Toll / Highway'),
        ('repair', 'Repair / Parts'),
        ('other',  'Other'),
    ], string='Expense Type', required=True, default='fuel')

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
    )

    # ─── FUEL-SPECIFIC ─────────────────────────────────────────────
    liters = fields.Float(
        string='Liters Filled',
        help='Applicable for Fuel type expenses.',
    )
    price_per_liter = fields.Float(string='Price per Liter (₹)')

    # ─── COST ──────────────────────────────────────────────────────
    cost = fields.Float(
        string='Total Cost (₹)',
        compute='_compute_cost',
        store=True,
        readonly=False,
    )

    notes = fields.Char(string='Notes')

    # ─── AUTO-CALCULATE FUEL COST ──────────────────────────────────
    @api.depends('liters', 'price_per_liter', 'expense_type')
    def _compute_cost(self):
        for expense in self:
            if (expense.expense_type == 'fuel'
                    and expense.liters
                    and expense.price_per_liter):
                expense.cost = expense.liters * expense.price_per_liter
            # else: user enters cost manually (leave unchanged)
