# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    ecs_period_id = fields.Many2one(
        'ecs.payroll.period',
        related='payslip_run_id.ecs_period_id',
        store=True,
        readonly=True,
    )
    ecs_days_outside_contract = fields.Float(
        string='Days Outside Contract',
        compute='_compute_ecs_days_outside_contract',
        store=True,
    )

    @api.depends(
        'date_from',
        'date_to',
        'version_id',
        'version_id.contract_date_start',
        'version_id.contract_date_end',
    )
    def _compute_ecs_days_outside_contract(self):
        for payslip in self:
            payslip.ecs_days_outside_contract = payslip._get_ecs_days_outside_contract()

    def _get_ecs_days_outside_contract(self):
        self.ensure_one()
        contract = self.version_id
        if not contract or not self.date_from or not self.date_to:
            return 0.0

        period_start = self.date_from
        period_end = self.date_to
        contract_start = contract.contract_date_start or period_start
        contract_end = contract.contract_date_end or period_end

        covered_start = max(period_start, contract_start)
        covered_end = min(period_end, contract_end)
        total_days = (period_end - period_start).days + 1
        covered_days = 0
        if covered_start <= covered_end:
            covered_days = (covered_end - covered_start).days + 1
        return float(max(total_days - covered_days, 0))

    def ecs_get_recurring_input_amount(self, input_code):
        self.ensure_one()
        if not self.version_id:
            return 0.0
        return self.version_id.get_recurring_input_amount(input_code, date=self.date_to)

    def ecs_get_variable_input_amount(self, input_code):
        self.ensure_one()
        if not self.version_id:
            return 0.0
        period_id = self.ecs_period_id.id if self.ecs_period_id else False
        return self.version_id.get_variable_input_amount(input_code, period_id=period_id)

    def ecs_get_income_tax_amount(self, taxable_amount):
        self.ensure_one()
        date = self.date_to or fields.Date.today()
        company_id = self.company_id.id if self.company_id else self.env.company.id
        return self.env['ecs.payroll.tax.bracket'].compute_tax(
            taxable_amount,
            date=date,
            company_id=company_id,
        )

    def _ecs_clean_mail_header(self, value):
        return (value or '').replace('\n', ' ').replace('\r', ' ').strip()

    def _ecs_get_payslip_mail_template(self):
        return self.env.ref('ecs_payroll.email_template_ecs_payslip', raise_if_not_found=False)

    def _ecs_get_payslip_email_values(self):
        self.ensure_one()
        employee_name = self._ecs_clean_mail_header(self.employee_id.name)
        period_name = self._ecs_clean_mail_header(self.ecs_period_id.name)
        email_from = self._ecs_clean_mail_header(
            getattr(self.company_id, 'email_formatted', False)
            or self.company_id.email
            or self.env.user.email_formatted
        )
        return {
            'subject': _('Payslip of %(employee)s for %(period)s') % {
                'employee': employee_name,
                'period': period_name or self.date_to or '',
            },
            'email_from': email_from,
            'email_to': self._ecs_clean_mail_header(self.employee_id.work_email),
        }

    def action_send_ecs_payslip_email(self):
        template = self._ecs_get_payslip_mail_template()
        if not template:
            raise UserError(_('ECS payslip email template is not installed.'))

        sent_count = 0
        skipped_names = []
        for payslip in self:
            if not payslip.employee_id.work_email:
                skipped_names.append(payslip.employee_id.name or payslip.name or str(payslip.id))
                continue
            template.send_mail(
                payslip.id,
                force_send=True,
                email_values=payslip._ecs_get_payslip_email_values(),
            )
            sent_count += 1
            _logger.info('ECS payslip email queued for %s', payslip.employee_id.name)

        if not sent_count:
            raise UserError(_('No payslip emails were sent because selected employees do not have work email addresses.'))
        if skipped_names:
            _logger.warning('Skipped ECS payslip emails without work email: %s', ', '.join(skipped_names))
        return True


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    ecs_period_id = fields.Many2one(
        'ecs.payroll.period',
        related='slip_id.ecs_period_id',
        store=True,
        readonly=True,
    )
    badge_id = fields.Char(related='employee_id.barcode', store=True, readonly=True)
