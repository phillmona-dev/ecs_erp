# -*- coding: utf-8 -*-
from odoo import fields, models


class EcsBudgetPosition(models.Model):
    """
    ECS-native budget position / budget line.
    Replaces account.budget.post (enterprise-only) so ECS ERP
    runs cleanly on Odoo 18 Community.
    """
    _name = 'ecs.budget.position'
    _description = 'ECS Budget Position'
    _order = 'company_id, name'

    name = fields.Char('Budget Line Name', required=True)
    code = fields.Char('Code', size=20, index=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    account_ids = fields.Many2many(
        'account.account',
        'ecs_budget_position_account_rel',
        'budget_position_id', 'account_id',
        string='Accounts',
        domain="[('deprecated','=',False)]",
    )
    active = fields.Boolean(default=True)
    notes = fields.Text('Notes')
