from odoo import models, fields
from odoo.exceptions import UserError


class Registration(models.Model):
    _name = 'registration.model'
    _description = 'Registration Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_name = fields.Char(string='Company Name')
    products_to_be_registered = fields.Many2many('product.product',string='Products to be Registered')

    country = fields.Char(string='Country')
    receiving_dossier_date = fields.Date(string='Receiving Dossier/Date')

    final_comment_received = fields.Char(string='Final Comment Received from Supplier')
    agency_agreement_linkage_date = fields.Date(string='Agency Agreement Linkage Date')
    submission_date = fields.Date(string='Submission Date',tracking=True)
    registration_no = fields.Char(string='Registration No')
    registration_type = fields.Selection([('new', 'New'), ('renewal', 'Renewal'), ('variation', 'Variation')], string='Registration Type')
    application_type = fields.Char(string='Application Type')
    fee_attached = fields.Date(string='Fee Attached')
    follow_up = fields.One2many('registration.model.details', 'header', string='Follow Up Details',tracking=True)
    evaluation = fields.One2many('registration.model.eval', 'header', string='Evaluation',tracking=True)
    product_type= fields.Selection([('medicine', 'Medicine'), ('device', 'Medical Device'), ('food', 'Food'), ('cosmetics', 'Cosmetics') ], string='Product Type',required=True)
    sterile = fields.Boolean("Is the product Sterile")

    eris_no = fields.Char(string='eRIS No')
    debit_note_request = fields.Date(string='Debit Note Request')
    actual_sample = fields.Char(string='Actual Sample and Others')
    batch_number = fields.Char(string='Batch Number')
    date_of_submission = fields.Date(string='Date of Submission')

    payment_details = fields.One2many('registered.product.detail','header', string='Payment Details')



    gmp_paid_date = fields.Date('GMP Inspection Pay Date')
    gmp_renewal_date = fields.Date('GMP Renewal Date')
    gmp_result = fields.Char('GMP Inspection Result')
    is_registered = fields.Boolean("Is registered", default=False)

    def get_users_for_roles(self, role, company_id):
        users = []
        roles = self.env['res.groups'].search([('name', '=', role)])

        for user in roles.users:
            if user.company_id.id == company_id:
                users.append(user.id)
        return users

    def send_activity(self, message, agreement, role):
        users = self.get_users_for_roles(role, self.env.user.company_id.id)
        for user in users:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('droga_regulatory.model_registration.model').id,
                'res_name': message,
                'res_id': agreement.id,
                'automated': True,
                'user_id': user.id,
                'activity_type_id': 4,
                'summary': message,
                'note': agreement['company_name']
            })

    def add_to_registered(self):
        if self.company_name and self.application_type and self.product_type and self.products_to_be_registered:
            products = [(6, 0, self.products_to_be_registered.ids)]
            list_of_products = [str(product.name) for product in self.products_to_be_registered]
            for record in self:
                message = "Products " + ",".join(list_of_products) + "has been registered with company name " + record.company_name
                record.is_registered = True
                self.send_activity(message, record, 'Regulatory Manager')
                self.send_activity(message, record, 'Regulatory Head')

            return {
                'name': 'Add to registered list Pop-up Form',
                'type': 'ir.actions.act_window',
                'res_model': 'create.registered.list',
                'view_mode': 'form',
                'target': 'new',
                'context':{
                    'default_company_name':self.company_name,
                    'default_applicant':self.application_type,
                    'default_product_type':self.product_type,
                    'default_product_name':products,
                }
            }
        else:
            raise UserError('Please fill in at least the Company Name, Application Type, Products to be Registered and Product Type!')


class Registrationdetails(models.Model):
    _name = 'registration.model.details'

    date = fields.Date(string='Date')
    status = fields.Char(string='Status')

    header = fields.Many2one('registration.model')

class Registrationeval(models.Model):
    _name = 'registration.model.eval'

    evaluation_comment = fields.Char(string='Evaluation Comment Sent to Supplier')
    sent_date = fields.Date('Date')
    header = fields.Many2one('registration.model')

class RegisteredProductDetail(models.Model):
    _name = 'registered.product.detail'

    payment_status = fields.Char(string='Payment Status')
    date = fields.Date('Date')
    header = fields.Many2one('registration.model')

class AddToRegistered(models.Model):
    _name = 'create.registered.list'

    company_name = fields.Char(string='Companies')
    applicant = fields.Char('Applicant')
    product_type = fields.Selection(
        [('medicine', 'Medicine'), ('device', 'Medical Device'), ('food', 'Food'), ('cosmetics', 'Cosmetics')],
        string='Product Type', required=True)

    product_name = fields.Many2many('product.product', string='Products')
    approval_date = fields.Date(string='Approval Date')
    validity_date = fields.Date(string='Validity Date')
    remark = fields.Text(string='Remark')
    registered_under = fields.Selection([('droga', 'Droga'), ('other', 'Other Agents')], string='Registered Under',
                                        required=True)
    pack_size = fields.Char('Pack Size')

    def create_registered(self):
        products = [(6, 0, self.product_name.ids)]
        if self.company_name and self.product_type and self.product_name and self.validity_date and self.approval_date and self.applicant and self.registered_under and self.pack_size:
            registered_list = self.env['droga.reg.final.registered.renewal'].create({
                'company_name': self.company_name,
                'applicant': self.applicant,
                'product_type': self.product_type,
                'product_name': products,
                'approval_date': self.approval_date,
                'validity_date': self.validity_date,
                'registered_under': self.registered_under,
                'pack_size': self.pack_size,
                'remark': self.remark,
            })
        else:
            raise UserError('Please fill in all the fields.')






