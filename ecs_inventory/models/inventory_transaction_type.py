# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcsInventoryTransactionType(models.Model):
    _name = 'ecs.inventory.transaction.type'
    _description = 'ECS Inventory Transaction Type'
    _inherit = ['mail.thread']
    _order = 'sequence, code, name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    operation_type = fields.Selection(
        [
            ('receipt', 'Receipt'),
            ('issue', 'Issue'),
            ('transfer', 'Internal Transfer'),
            ('adjustment', 'Adjustment'),
            ('return', 'Return'),
            ('consumption', 'Internal Consumption'),
        ],
        required=True,
        default='transfer',
        tracking=True,
    )
    source_usage = fields.Selection(
        selection='_selection_location_usage',
        string='Default Source Usage',
    )
    destination_usage = fields.Selection(
        selection='_selection_location_usage',
        string='Default Destination Usage',
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Default Operation Type',
        check_company=True,
    )
    requires_lot = fields.Boolean(
        string='Requires Batch / Serial',
        help='Use for inventory flows that must be traceable by lot or serial number.',
    )
    affects_valuation = fields.Boolean(default=True)
    notes = fields.Text()
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            'ecs_inventory_transaction_type_code_company_uniq',
            'unique(code, company_id)',
            'The transaction type code must be unique per company.',
        ),
    ]

    @api.model
    def _selection_location_usage(self):
        return self.env['stock.location']._fields['usage'].selection

    @api.constrains('source_usage', 'destination_usage')
    def _check_location_usage_direction(self):
        for transaction_type in self:
            if (
                transaction_type.source_usage
                and transaction_type.destination_usage
                and transaction_type.source_usage == transaction_type.destination_usage
                and transaction_type.operation_type not in ('transfer', 'adjustment')
            ):
                raise ValidationError(
                    'Source and destination usage should differ for this transaction type.'
                )

    @api.onchange('operation_type')
    def _onchange_operation_type_defaults(self):
        defaults = {
            'receipt': ('supplier', 'internal'),
            'issue': ('internal', 'customer'),
            'transfer': ('internal', 'internal'),
            'adjustment': ('inventory', 'internal'),
            'return': ('customer', 'internal'),
            'consumption': ('internal', 'production'),
        }
        for transaction_type in self:
            if transaction_type.operation_type in defaults:
                (
                    transaction_type.source_usage,
                    transaction_type.destination_usage,
                ) = defaults[transaction_type.operation_type]
