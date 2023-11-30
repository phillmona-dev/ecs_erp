from datetime import timedelta

from odoo import models, fields

class AgencyAgreement(models.Model):
    _name = 'droga.reg.agency.agreement.header'
    _description = 'Agency Agreement Follow Up Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    details = fields.One2many('droga.reg.agency.agreement.detail', 'header', string='Agreement Details')
    unique_id = fields.Char('U_id')

    name = fields.Char(string='Name')
    phone = fields.Char(string='Phone')
    applicant_type = fields.Selection([("first", "First Agent"), ("second", "Second Agent"), ("third", "Third Agent")],
                                      string='Application Type')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    status = fields.Selection([("active", "Active"), ("inactive", "Inactive"), ("pending", "Pending")], string='Status')
    extension_date = fields.Date(string='Extension Date')




class AgencyAgreementDet(models.Model):
    _name = 'droga.reg.agency.agreement.detail'

    name = fields.Char(string='Name')
    phone = fields.Char(string='Phone')
    applicant_type = fields.Selection([("first", "First Agent"), ("second", "Second Agent"), ("third", "Third Agent")],
                                      string='Application Type')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    status = fields.Selection([("active", "Active"), ("inactive", "Inactive"), ("pending", "Pending")], string='Status')
    extension_date = fields.Date(string='Extension Date')
    header = fields.Many2one('droga.reg.agency.agreement.header')


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
                'res_model_id': self.env.ref('droga_regulatory.model_droga_reg_agency_agreement_header').id,
                'res_name': message,
                'res_id': agreement.id,
                'automated': True,
                'user_id': user.id,
                'activity_type_id': 4,
                'summary': message,
                'note': agreement['name']
            })

    def send_insurance_reminder(self):
        today = fields.Date.today()
        three_month_from_now = today + timedelta(days=90)

        agreement_due_date = self.search([('end_date', '=', three_month_from_now)])
        print(agreement_due_date)
        for agreement in agreement_due_date:
            message = "The due date for the agreement " + agreement.name + " is only 3 months away!"
            self.notify(message)
            self.activity(message, agreement)
