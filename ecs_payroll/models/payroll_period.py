# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EcsPayrollPeriod(models.Model):
    _name = 'ecs.payroll.period'
    _description = 'ECS Payroll Period'
    _order = 'company_id, date_start desc, date_end desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    state = fields.Selection(
        [
            ('open', 'Open'),
            ('closed', 'Closed'),
        ],
        default='open',
        required=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'period_name_company_unique',
            'unique(name, company_id)',
            'Payroll period name must be unique per company.',
        ),
    ]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for period in self:
            if period.date_start and period.date_end and period.date_start > period.date_end:
                raise ValidationError(_('Payroll period end date cannot be before start date.'))

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'open'})
