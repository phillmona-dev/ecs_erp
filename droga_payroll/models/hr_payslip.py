from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    days_outside_contract = fields.Float(string="Days Outside Contract", compute="_compute_days_outside_contract")
    period = fields.Many2one(related="payslip_run_id.period", store=True)
    mail_server = fields.Char(compute="get_outgoing_email")
    

    @api.depends('employee_id', 'date_from', 'date_to')
    def get_outgoing_email(self):
        self.mail_server = ""
        # Search for the outgoing mail server with the lowest priority (default)
        mail_servers = self.env['ir.mail_server'].search([], order='sequence', limit=1)

        if mail_servers:
            self.mail_server = mail_servers.smtp_user

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_days_outside_contract(self):
        for payslip in self:
            contract = self.env['hr.contract'].search([('employee_id', '=', payslip.employee_id.id)], limit=1)
            if not contract:
                payslip.days_outside_contract = 0
                continue

            date_from = payslip.date_from
            date_to = payslip.date_to

            contract_days = self._get_contractual_workdays(contract, date_from, date_to)

            payslip.days_outside_contract = contract_days

    def _get_contractual_workdays(self, contract, date_from, date_to):
        total_days = (date_to - date_from).days + 1
        total_working_days = (date_to - contract.date_start).days + 1

        if total_working_days >= total_days:
            return 0
        else:
            return 30 - total_working_days

    def send_email_with_attachment(self, record_id, attachment):
        template_id = self.env.ref('droga_payroll.email_template_payslip').id
        email_template = self.env['mail.template'].browse(template_id)
        # Attach the file
        attachment_id = self.env['ir.attachment'].create({
            'name': attachment.name,
            'type': 'binary',
            'datas': attachment.datas,
            'store_fname': attachment.store_fname,
            'mimetype': attachment.mimetype,
            'res_model': 'your.model',
            'res_id': record_id,
        })
        # Send the email
        email_template.send_mail(record_id, force_send=True,
                                 email_values={'attachment_ids': [(6, 0, [attachment_id.id])]})

    def action_send_email(self):
        mail_template = self.env.ref('droga_payroll.email_template_payslip')
        mail_template.send_mail(self.id, force_send=True)


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    period = fields.Many2one(related="slip_id.payslip_run_id.period", store=True)
    badge_id = fields.Char(related="employee_id.barcode")
