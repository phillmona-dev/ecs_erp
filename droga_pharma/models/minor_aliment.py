from datetime import datetime
from email.policy import default
from odoo import models, fields, api

class droga_pharma_minor_alignment(models.Model):
    _name = 'droga.pharma.minor.alignment'
    _description = 'Droga Minor Alignments'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    #Text fields
    minor_align=fields.Char("Minor ailment",required=True)
    decision = fields.Selection(
        [('Advice only', 'Advice only'), ('Advice and treatment', 'Advice and treatment')])
    referral=fields.Selection(
        [('Urgent', 'Urgent'), ('Appointment', 'Appointment')])

    treatment=fields.Many2many('product.template')

    # Related fields
    client = fields.Many2one('res.partner', related='sales_origin.partner_id')
    customer = fields.Many2one('droga.pharma.cust.employees', related='sales_origin.customer_emp')
    client_descr = fields.Char(related='sales_origin.emp_descr')
    sales_origin = fields.Many2one('sale.order')
    mobile = fields.Char("Mobile", related='customer.phone_no', store=True)
    medical = fields.Html("Medical History", related="customer.medical_history", store=True)
    medication_history = fields.Html("Medication History and adherence", related='customer.medication_history',
                                     store=True)
    dob = fields.Date("Date of Birth", compute="_get_dob", store=True)
    age = fields.Integer("Age", compute="_compute_age", readonly=True)
    gender = fields.Selection(selection=[("Male", "Male"), ("Female", "Female")], string="Gender",
                              related='customer.gender', store=True)
    profession = fields.Selection(selection=[("hp", "Health Professional"), ("other", "Other")], string="Profession",
                                  related="customer.profession", store=True)
    # weight = fields.Float("Weight")
    # height = fields.Float("Height")
    # bsa = fields.Float("BSA")
    address = fields.Char("Address")
    # pregnancy = fields.Char("Pregnancy status")
    immunization = fields.Html("Immunization", related="customer.immunization", store=True)
    adr = fields.Html("ADRS and/or Allergies", related="customer.adr_allergy", store=True)
    diagnosis = fields.Text("Diagnosis")
    physician = fields.Char("Primary physician and contact information")
    next_date = fields.Date("Next appointment date")
    @api.depends("dob")
    def _compute_age(self):
        for record in self:
            if record.dob:
                record.age = datetime.now().year - record.dob.year
            else:
                record.age = 0

    def _get_dob(self):
        for rec in self:
            if rec.customer.dob:
                rec.dob = rec.customer.dob
            else:
                rec.dob = datetime.now()

    def create_an_activity(self,rec, user_id, message):
        self.env['mail.activity'].sudo().create({
            'res_model_id': self.env.ref('droga_pharma.model_droga_pharma_minor_alignment').id,
            'res_name': message,
            'res_id': rec.id,
            'automated': True,
            'user_id': user_id,
            'activity_type_id': 4,
            'summary': message,
            'note': message
        })

    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_id', '=', self.id)])
        if activity:
            activity.sudo().action_done()

    def mtm_schedule(self):
        today = fields.Date.today()
        records = self.search([('next_date', '=', today)])
        for rec in records:
            message = "The customer "+rec.client_descr+" has an appointment for "+rec.minor_align
            self.create_an_activity(rec, rec.create_uid.id, message)
