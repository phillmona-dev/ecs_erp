# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class EcsPayrollTaxBracket(models.Model):
    _name = 'ecs.payroll.tax.bracket'
    _description = 'ECS Payroll Tax Bracket'
    _order = 'company_id, date_from desc, lower_bound'

    name = fields.Char(compute='_compute_name', store=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date()
    lower_bound = fields.Float(required=True, digits=(12, 2))
    upper_bound = fields.Float(
        digits=(12, 2),
        help='Use 0.00 for the open-ended top bracket.',
    )
    rate = fields.Float(
        required=True,
        digits=(12, 4),
        help='Percentage rate applied to the taxable amount.',
    )
    deduction = fields.Float(digits=(12, 2))
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'tax_bracket_company_date_lower_unique',
            'unique(company_id, date_from, lower_bound)',
            'Tax bracket lower bounds must be unique per company and effective date.',
        ),
    ]

    @api.depends('lower_bound', 'upper_bound', 'rate')
    def _compute_name(self):
        for bracket in self:
            upper = bracket.upper_bound or _('Above')
            bracket.name = _('%(lower).2f - %(upper)s @ %(rate).2f%%') % {
                'lower': bracket.lower_bound,
                'upper': upper,
                'rate': bracket.rate,
            }

    @api.constrains('date_from', 'date_to', 'lower_bound', 'upper_bound', 'rate', 'deduction')
    def _check_values(self):
        for bracket in self:
            if bracket.date_to and bracket.date_from > bracket.date_to:
                raise ValidationError(_('Tax bracket end date cannot be before start date.'))
            if bracket.lower_bound < 0 or bracket.upper_bound < 0:
                raise ValidationError(_('Tax bracket bounds cannot be negative.'))
            if bracket.upper_bound and bracket.upper_bound < bracket.lower_bound:
                raise ValidationError(_('Tax bracket upper bound cannot be below lower bound.'))
            if bracket.rate < 0 or bracket.deduction < 0:
                raise ValidationError(_('Tax bracket rate and deduction cannot be negative.'))

    @api.model
    def get_bracket(self, taxable_amount, date=None, company_id=None):
        date = date or fields.Date.today()
        company_id = company_id or self.env.company.id
        amount = max(taxable_amount or 0.0, 0.0)
        return self.search([
            ('company_id', '=', company_id),
            ('date_from', '<=', date),
            '|', ('date_to', '=', False), ('date_to', '>=', date),
            ('lower_bound', '<=', amount),
            '|', ('upper_bound', '=', 0.0), ('upper_bound', '>=', amount),
            ('active', '=', True),
        ], order='date_from desc, lower_bound desc', limit=1)

    @api.model
    def compute_tax(self, taxable_amount, date=None, company_id=None):
        bracket = self.get_bracket(taxable_amount, date=date, company_id=company_id)
        if not bracket:
            return 0.0
        amount = max(taxable_amount or 0.0, 0.0)
        return max((amount * bracket.rate / 100.0) - bracket.deduction, 0.0)
