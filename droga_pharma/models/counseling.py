from datetime import datetime
from email.policy import default
from odoo import models, fields, api

class droga_pharma_counselling(models.Model):
    _name = 'droga.pharma.counselling'

    #Text fields
    # area_counsel=fields.Many2one('droga.pharma.area_counsel',string='Area of counselling')
    coun_code = fields.Char("Counselling session ID", default=lambda self: self.env['ir.sequence'].next_by_code('droga.pharma.counselling.session.sequence'), readonly=True)
    counselling_cat = fields.Selection(selection=[('life_style', 'Life style'), ('medication_use', 'Medication Use')], string='Area of counselling',required=True)
    description = fields.Char("Area of counselling description")
    status=fields.Char("Status")
    ses_acceptance= fields.Selection([('Accepted', 'Accepted'), ('Rejected', 'Rejected')],string="Acceptance")
    pharmacist_lev_understanding=fields.Selection([('High', 'High'), ('Optimal', 'Optimal'),('Low', 'Low')],string='Pharmacist level of understanding')
    assessment = fields.Html("Assessment")
    date=fields.Date('Date',default=datetime.today())
    sales_origin = fields.Many2one('sale.order',required=True)
    counselling_given = fields.Html("Counselling given")
    patient_lev_understanding=fields.Selection([('High', 'High'), ('Optimal', 'Optimal'),('Low', 'Low')],string='Patient Level of understanding')
    # Related fields
    client = fields.Many2one('res.partner')
    client_descr = fields.Char(related='client.name')
    customer = fields.Many2one('droga.pharma.cust.employees', related='sales_origin.customer_emp')
    mobile = fields.Char("Mobile", compute='get_cust_hist', store=True, inverse='inverse_mobile', tracking=True)
    dob = fields.Date("Date of Birth", store=True, compute='get_cust_hist', inverse='inverse_dob')
    age = fields.Integer("Age", compute="_compute_age", readonly=True)
    gender = fields.Selection(selection=[("Male", "Male"), ("Female", "Female")], string="Gender", store=True,
                              compute='get_cust_hist', inverse='update_gender')

    medical = fields.Html("Medical History", store=True, compute='get_cust_hist', inverse='update_medical',
                          tracking=True)
    medication_history = fields.Html("Medication History and adherence", store=True, compute='get_cust_hist',
                                     inverse='update_medication_history', tracking=True)
    immunization = fields.Html("Immunization", store=True, compute='get_cust_hist', inverse='update_immunization',
                               tracking=True)
    adr = fields.Html("ADRS and/or Allergies", store=True, compute='get_cust_hist', inverse='update_adr', tracking=True)

    def get_cust_hist(self):
        for rec in self:
            rec.medical = rec.client.medical_history
            rec.medication_history = rec.client.medication_history
            rec.immunization = rec.client.immunization
            rec.adr = rec.client.adr_allergy
            rec.dob = rec.client.dob
            rec.gender = rec.client.gender
            rec.mobile = rec.client.mobile

    def update_adr(self):
        for rec in self:
            rec.client.adr_allergy = rec.adr

    def update_immunization(self):
        for rec in self:
            rec.client.immunization = rec.immunization
    def update_gender(self):
        for rec in self:
            rec.client.gender=rec.gender
    def update_medication_history(self):
        for rec in self:
            rec.client.medication_history = rec.medication_history

    def update_medical(self):
        for rec in self:
            rec.client.medical_history = rec.medical

    _sql_constraints = [
        ('sales_consulting', 'unique (sales_origin)',
         'Only a single counselling session can be conducted per sales order.')
    ]

    def inverse_dob(self):
        for rec in self:
            rec.client.dob = rec.dob

    def inverse_mobile(self):
        for rec in self:
            rec.client.mobile = rec.mobile
    @api.depends("dob")
    def _compute_age(self):
        for record in self:
            if record.dob:
                record.age = datetime.now().year - record.dob.year
            else:
                record.age = 0


    profession = fields.Selection(selection=[("hp", "Health Professional"), ("other", "Other")], string="Profession", store=True)
    weight = fields.Float("Weight")
    height = fields.Float("Height")
    bsa = fields.Float("BSA")
    address = fields.Char("Address")
    pregnancy = fields.Boolean("Pregnancy status")
    diagnosis = fields.Text("Diagnosis")
    physician = fields.Char("Primary physician and contact information")
