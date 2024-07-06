from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    # add year and period
    fiscal_year = fields.Many2one("account.fiscal.year", "Fiscal Year")
    period = fields.Many2one("account.fiscal.year.period", domain="[('fiscal_year_id', '=', fiscal_year)]")

    date_start = fields.Date(string='Date From')
    date_end = fields.Date(string='Date To')

    def action_paid(self):
        # Call the original 'action_paid' method
        result = super(HrPayslipRun, self).action_paid()
        # update variable transactions to paid
        variable_transactions = self.env["hr.payroll.variable.payment"].search([('period', '=', self.period.id)])

        for record in variable_transactions:
            record.write({'status': 'Paid'})

        return result

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

    def action_send_payslip_email(self):

        if self.state == 'close':

            mail_template = self.env.ref('droga_payroll.email_template_payslip')

            for record in self.slip_ids:
                if record.employee_id.work_email:
                    mail_template.send_mail(record.id, force_send=True)
        else:
            raise ValidationError(
                "The status must be changed to done to send payslip email")

    @api.onchange("period")
    def _on_period_change(self):
        for record in self:
            record.date_start = record.period.date_from
            record.date_end = record.period.date_to
