# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EcsCompanyProfile(models.Model):
    _name = 'ecs.company.profile'
    _description = 'ECS Company Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'company_id'
    _order = 'sequence, company_id'

    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        index=True,
        ondelete='cascade',
        tracking=True,
    )
    company_code = fields.Selection(
        [
            ('import_export', 'Import & Export'),
            ('construction', 'Construction'),
            ('school', 'Private School'),
        ],
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    requires_sales = fields.Boolean(compute='_compute_required_modules', store=True)
    requires_project = fields.Boolean(compute='_compute_required_modules', store=True)
    requires_school_operations = fields.Boolean(compute='_compute_required_modules', store=True)
    notes = fields.Text()

    _sql_constraints = [
        ('company_profile_company_unique', 'unique(company_id)', 'Each company can have only one ECS profile.'),
    ]

    @api.depends('company_code')
    def _compute_required_modules(self):
        for profile in self:
            profile.requires_sales = profile.company_code == 'import_export'
            profile.requires_project = profile.company_code == 'construction'
            profile.requires_school_operations = profile.company_code == 'school'
