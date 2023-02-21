from odoo import models, fields, api


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    # add year and period
    fiscal_year = fields.Many2one("account.fiscal.year", "Fiscal Year")
    period = fields.Many2one("account.fiscal.year.period", domain="[('fiscal_year_id', '=', fiscal_year)]")

    date_start = fields.Date(string='Date From')
    date_end = fields.Date(string='Date To')

    def droga_payroll_sheet_report_action(self):
        view = self.env.ref(
            'droga_payroll.droga_payroll_sheet_report_form')

        return {
            'name': 'Payroll Master Report',
            'view_mode': 'form',
            'res_model': 'hr.payslip.run.report',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_batch': self.id
            }
        }

    @api.onchange("period")
    def _on_period_change(self):
        for record in self:
            record.date_start = record.period.date_from
            record.date_end = record.period.date_to
