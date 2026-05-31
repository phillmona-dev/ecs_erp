# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

ETHIOPIAN_RETIREMENT_AGE = 60


class HrEmployee(models.Model):
    """
    Employee extensions for ECS ERP.

    Provides company-scoped divisions, employee codes, Ethiopian HR dates,
    banking information, and employee compliance identifiers.
    """
    _inherit = 'hr.employee'

    # ── Ethiopian Identity ─────────────────────────────────────────────
    amharic_name = fields.Char('Amharic Name', tracking=True)
    tin_no       = fields.Char('TIN Number', tracking=True)
    pension_no   = fields.Char('Pension Number', tracking=True)

    # ── Bank Details ──────────────────────────────────────────────────
    bank_name       = fields.Many2one('res.bank', 'Bank')
    bank_account_no = fields.Char('Bank Account Number')

    # ── Employee Code ─────────────────────────────────────────────────
    employee_code = fields.Char(
        'Employee ID', copy=False, readonly=True, index=True,
        help='Auto-generated unique employee identifier.'
    )

    # ── Organisation ──────────────────────────────────────────────────
    division_id = fields.Many2one(
        'ecs.hr.division', 'Division / Business Unit',
        domain="[('company_id','=',company_id)]",
        tracking=True,
    )

    # ── Ethiopian HR Dates ────────────────────────────────────────────
    hire_date = fields.Date(
        'Hire Date', tracking=True,
        help='Actual date the employee joined the company.',
    )
    retire_date = fields.Date(
        'Expected Retirement Date',
        compute='_compute_retire_date', store=True,
        help=f'Computed as birthday + {ETHIOPIAN_RETIREMENT_AGE} years '
             f'(Ethiopian Labour Law Article 109).',
    )
    years_of_service = fields.Float(
        'Years of Service',
        compute='_compute_years_of_service',
        help='Years from hire date to today.',
    )

    # ── Compute ───────────────────────────────────────────────────────

    @api.depends('birthday')
    def _compute_retire_date(self):
        for emp in self:
            if emp.birthday:
                emp.retire_date = emp.birthday + relativedelta(years=ETHIOPIAN_RETIREMENT_AGE)
            else:
                emp.retire_date = False

    @api.depends('hire_date')
    def _compute_years_of_service(self):
        today = fields.Date.today()
        for emp in self:
            if emp.hire_date:
                delta = relativedelta(today, emp.hire_date)
                emp.years_of_service = round(delta.years + delta.months / 12.0, 2)
            else:
                emp.years_of_service = 0.0

    # ── Employee ID Sequence ──────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('employee_code'):
                vals['employee_code'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix='EMP',
                    date=fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    # ── Constrains ────────────────────────────────────────────────────

    @api.constrains('birthday', 'hire_date')
    def _check_hire_date(self):
        for emp in self:
            if emp.hire_date and emp.birthday and emp.hire_date < emp.birthday:
                raise ValidationError(
                    _('Hire date (%s) cannot be before date of birth (%s) for employee: %s')
                    % (emp.hire_date, emp.birthday, emp.name)
                )

    # ── Onchange ──────────────────────────────────────────────────────

    @api.onchange('company_id')
    def _onchange_company_clear_division(self):
        """Clear division when company changes — avoid cross-company division."""
        self.division_id = False
