import uuid

from odoo import models, fields, api
from odoo.exceptions import UserError


class CompanyInfo(models.Model):
    _name = 'droga.reg.company.info'
    _description = 'Company Information'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reg_num'

    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.reg_num)])
        if activity:
            activity.sudo().action_done()

    def get_users_for_roles(self, role, company_id):
        users = []
        roles = self.env['res.groups'].search([('name', '=', role)])

        for user in roles.users:
            if user.company_id.id == company_id:
                users.append(user.id)
        return users

    def generate_unique_sequence(self):
        id_exists = True
        while id_exists:
            new_id = uuid.uuid4()
            new_id = str(new_id).replace('-', '')
            existing_record = self.env['droga.reg.agency.agreement.header'].search([('unique_id', '=', new_id)])
            if not existing_record:
                id_exists = False
        return new_id



    def create_activity(self, user_id, message):
        # create mail activity for the approval
        todos = dict(res_id=self.id,
                     res_model_id = self.env['ir.model'].search([('model', '=', 'droga.reg.company.info')]).id,
                     user_id=user_id, summary= message, note= message,
                     activity_type_id=4,
                     date_deadline=fields.datetime.now())
        self.env['mail.activity'].sudo().create(todos)


    reg_num = fields.Char('Registration Number', default=lambda self: self.env['ir.sequence'].next_by_code('droga.reg.exhibition_registration.sequence'),
                              readonly=True)
    status = fields.Selection([('registered', 'Registered') , ('reviewed', 'Reviewed')],  string='Registration Status in Ethiopia' , default='registered')



    company_name = fields.Char(string='Company Name')
    phone = fields.Char(string='Phone')
    country = fields.Char(string='Country')
    registration_status = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Registration Status in Ethiopia')
    registered_products_agent = fields.Many2many('droga.bdr.agents',string='Registered Products and its Agent', required=False)
    gmp_approval_status = fields.Char(string='GMP Approval Status')
    email = fields.Char(string='Email')
    phone_no = fields.Char(string='Phone Number')
    website = fields.Char(string='Website')
    remark = fields.Char(string='Remark')
    products_list = fields.Many2many('product.product',string='Products List')
    follow_up = fields.One2many('droga.reg.follow.up', 'company_info', string='Follow Up')


    applicant_type = fields.Selection([("first", "First Agent"), ("second", "Second Agent"), ("third", "Third Agent"), ("exclusice", "Exclusive"), ("unexclusive", "Unexclusive")],
                                      string='Application Type')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    extension_date = fields.Date(string='Extension Date')
    tracking_number = fields.Char('Tracking Number')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    agreement_status = fields.Selection([("active", "Active"), ("inactive", "Inactive"), ("pending", "Pending")], string='Agreement Status', tracking=True)
    document_sent = fields.Boolean("Document Attached")


    bd_status = fields.Selection(
        [("recorded", "Recorded"), ("evolved", "Evolved"), ("agreement", "Agreement Reached")], default='recorded',
        required=True, readonly=True)

    def submit_to_ra(self):
        if self.tracking_number and self.company_name:
            users = self.get_users_for_roles('Regulatory Manager', self.company_id.id)
            message_dev_complete = 'Business Development Completed'
            for user in users:
                self.create_activity(user, message_dev_complete)
            for record in self:
                record.bd_status = 'agreement'
                if record.document_sent:
                    message_doc_sent = 'Document has been sent for ' + record.reg_num
                    for user in users:
                        self.create_activity(user, message_doc_sent)
        else:
            raise UserError('Please Fill in tracking number and company name.')

    @api.onchange('agreement_status')
    def agreement_change(self):
        if self.agreement_status != "pending":
            self.set_activity_done()



    def update_status(self,reg):
        request = self.search([('reg_num', '=', reg)], limit=1)
        if request:
            request.bd_status = 'evolved'


class follow_up(models.Model):
    _name = 'droga.reg.follow.up'

    follow_up_status = fields.Char(string='Follow up status')
    company_info = fields.Many2one('droga.reg.company.info', string='Follow Up')