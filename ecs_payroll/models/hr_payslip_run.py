# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    ecs_period_id = fields.Many2one(
        'ecs.payroll.period',
        string='ECS Payroll Period',
        domain="[('company_id','=',company_id),('state','=','open')]",
    )
    division_id = fields.Many2one(
        'ecs.hr.division',
        string='Division',
        domain="[('company_id','=',company_id)]",
    )

    def _get_valid_version_ids(self, date_start=None, date_end=None, structure_id=None, company_id=None, employee_ids=None, schedule_pay=None):
        version_ids = super()._get_valid_version_ids(
            date_start=date_start,
            date_end=date_end,
            structure_id=structure_id,
            company_id=company_id,
            employee_ids=employee_ids,
            schedule_pay=schedule_pay,
        )
        if not self.division_id:
            return version_ids
        versions = self.env['hr.version'].browse(version_ids).filtered(
            lambda version: version.employee_id.division_id == self.division_id
        )
        return versions.ids

    def action_paid(self):
        result = super().action_paid()
        for batch in self.filtered('ecs_period_id'):
            self.env['ecs.payroll.variable.input'].search([
                ('period_id', '=', batch.ecs_period_id.id),
                ('company_id', '=', batch.company_id.id),
                ('state', '=', 'approved'),
            ]).action_mark_paid()
            batch.ecs_period_id.action_close()
        return result

    @api.onchange('ecs_period_id')
    def _onchange_ecs_period_id(self):
        for batch in self:
            if batch.ecs_period_id:
                batch.date_start = batch.ecs_period_id.date_start
                batch.date_end = batch.ecs_period_id.date_end

    def action_open_ecs_payroll_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payroll Report',
            'res_model': 'ecs.payroll.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
                'default_period_id': self.ecs_period_id.id,
                'default_company_id': self.company_id.id,
                'default_division_id': self.division_id.id,
            },
        }

    def action_send_ecs_payslip_email(self):
        for batch in self:
            batch.slip_ids.action_send_ecs_payslip_email()
        return True
