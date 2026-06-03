# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EcsPayrollRate(models.Model):
    _name = 'ecs.payroll.rate'
    _description = 'ECS Payroll Rate'
    _order = 'company_id, code, date_from desc'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    rate = fields.Float(required=True, digits=(12, 4))
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'rate_code_company_date_unique',
            'unique(code, company_id, date_from)',
            'A payroll rate code can only be defined once per company and start date.',
        ),
    ]

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rate in self:
            if rate.date_to and rate.date_from > rate.date_to:
                raise ValidationError(_('Rate end date cannot be before start date.'))

    @api.model
    def get_rate(self, code, date=None, company_id=None):
        date = date or fields.Date.today()
        company_id = company_id or self.env.company.id
        rate = self.search([
            ('code', '=', code),
            ('company_id', '=', company_id),
            ('date_from', '<=', date),
            '|', ('date_to', '=', False), ('date_to', '>=', date),
            ('active', '=', True),
        ], order='date_from desc', limit=1)
        return rate.rate if rate else 0.0
