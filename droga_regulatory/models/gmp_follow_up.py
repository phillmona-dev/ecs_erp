from datetime import timedelta

from odoo import models, fields

class GmpInspection(models.Model):
    _name = 'droga.reg.gmp.inspection'
    _description = 'GMP Inspection Follow Up Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    company_name = fields.Char(string='Company Name')
    product_line_description = fields.Char(string='Product Line Description')
    gmp_application_date = fields.Date(string='GMP Application Date')
    fee_letter_receival_date = fields.Date(string='GMP Fee Letter Receival Date')
    fee_paid_submit_date = fields.Date(string='Fee Paid and Submitted to Inspection On')
    scheduled_inspection_date = fields.Date(string='Scheduled for Inspection Date')
    inspection_report_receival_date = fields.Date(string='Inspection Report Received Date')
    gmp_certificate_receival_date = fields.Date(string='GMP Certificate Received Date')
    renewal = fields.Boolean(string='Renewal')
    contract_renewal = fields.Date(string='Renewal')
    remark = fields.Text(string='Remark')

    def get_users_for_roles(self, role, company_id):
        users = []
        roles = self.env['res.groups'].search([('name', '=', role)])

        for user in roles.users:
            if user.company_id.id == company_id:
                users.append(user.id)
        return users

    def notify(self, message):
        users = self.get_users_for_roles('Regulatory Manager', self.env.user.company_id.id)
        for user in users:
            self.env['bus.bus']._sendone(user.id, "simple_notification", {
                "title": "Reminder for due date",
                "message": message,
                "sticky": True,
                "warning": True
            })

    def activity(self, message, agreement):
        users = self.get_users_for_roles('Regulatory Manager', self.env.user.company_id.id)
        for user in users:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('droga_regulatory.model_droga_reg_gmp_inspection').id,
                'res_name': message,
                'res_id': agreement.id,
                'automated': True,
                'user_id': user.id,
                'activity_type_id': 4,
                'summary': message,
                'note': agreement['company_name']
            })

    def send_insurance_reminder(self):
        today = fields.Date.today()
        three_month_from_now = today + timedelta(days=90)

        agreement_due_date = self.search([('contract_renewal', '=', three_month_from_now)])
        for agreement in agreement_due_date:
            message = "The due date for the agreement " + agreement.company_name + " is only 3 months away!"
            self.notify(message)
            self.activity(message, agreement)