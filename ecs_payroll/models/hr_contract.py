# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrContractEcs(models.Model):
    """Extend standard hr.contract with ECS Ethiopian payroll fields."""
    _inherit = 'hr.contract'

    housing_allowance = fields.Float(default=0.0, tracking=True)
    transport_allowance = fields.Float(default=0.0, tracking=True)
    representation_allowance = fields.Float(default=0.0, tracking=True)
    fuel_allowance = fields.Float(default=0.0, tracking=True)
    acting_allowance = fields.Float(default=0.0, tracking=True)
    telephone_allowance = fields.Float(default=0.0, tracking=True)
    pension_contribution = fields.Boolean(default=True, tracking=True)
    is_sales_employee = fields.Boolean(
        string='Sales Employee',
        help='Used by payroll rules for sales transport allowance treatment.',
    )
    uses_canteen = fields.Boolean(string='Uses Canteen Service')
    has_company_vehicle = fields.Boolean()
    paid_by_usd = fields.Boolean(string='Paid in USD')
    sales_commission = fields.Float(default=0.0)
    recurring_input_ids = fields.One2many(
        'ecs.payroll.recurring.input',
        'contract_id',
        string='Recurring Payments and Deductions',
    )
    payroll_input_type_ids = fields.Many2many(
        'ecs.payroll.input.type',
        string='Enabled Payroll Input Types',
    )

    @api.model
    def get_active_rate(self, code, date=None, company_id=None):
        return self.env['ecs.payroll.rate'].get_rate(code, date=date, company_id=company_id)

    @api.model
    def get_income_tax_amount(self, taxable_amount, date=None, company_id=None):
        return self.env['ecs.payroll.tax.bracket'].compute_tax(
            taxable_amount,
            date=date,
            company_id=company_id,
        )

    def get_recurring_input_amount(self, input_code, date=None):
        self.ensure_one()
        date = date or fields.Date.today()
        inputs = self.recurring_input_ids.filtered(
            lambda record: record.active
            and record.input_type_id.code == input_code
            and record.date_from <= date
            and (not record.date_to or record.date_to >= date)
        )
        return sum(inputs.mapped('amount'))

    def get_variable_input_amount(self, input_code, period_id=False):
        self.ensure_one()
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('input_type_id.code', '=', input_code),
            ('state', '=', 'approved'),
        ]
        if period_id:
            domain.append(('period_id', '=', period_id))
        return sum(self.env['ecs.payroll.variable.input'].search(domain).mapped('amount'))
