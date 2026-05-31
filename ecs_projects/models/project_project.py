# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    ecs_project_code = fields.Char(string='ECS Project Code', copy=False, index=True)
    ecs_project_category = fields.Selection(
        [
            ('internal', 'Internal'),
            ('client', 'Client'),
            ('construction', 'Construction'),
            ('operations', 'Operations'),
        ],
        string='ECS Project Category',
        default='internal',
        tracking=True,
    )
    ecs_approved_amount = fields.Monetary(
        string='Approved Amount',
        currency_field='company_currency_id',
        tracking=True,
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True,
    )
