from datetime import datetime
from email.policy import default
from odoo import models, fields, api

class droga_pharma_counselling(models.Model):
    _name = 'droga.pharma.counselling'

    #Text fields
    area_counsel=fields.Many2one('droga.pharma.area_counsel',string='Area of counselling')
    status=fields.Char("Status")
    ses_acceptance= fields.Selection([('Accepted', 'Accepted'), ('Rejected', 'Rejected')],string="Acceptance")
    pharmacist_lev_understanding=fields.Selection([('High', 'High'), ('Optimal', 'Optimal'),('Low', 'Low')],string='Pharmacist level of understanding')
    assessment = fields.Html("Assessment")
    date=fields.Date('Date')
    sales_origin = fields.Many2one('sale.order')
    counselling_given = fields.Html("Counselling given")
    patient_lev_understanding=fields.Selection([('High', 'High'), ('Optimal', 'Optimal'),('Low', 'Low')],string='Patient Level of understanding')

    # Related fields
    client = fields.Many2one('res.partner', related='sales_origin.partner_id')
    client_descr = fields.Char(related='sales_origin.emp_descr')
    customer = fields.Many2one('droga.pharma.cust.employees', related='sales_origin.customer_emp')
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
    weight = fields.Float("Weight")
    height = fields.Float("Height")
    bsa = fields.Float("BSA")
    address = fields.Char("Address")
    pregnancy = fields.Boolean("Pregnancy status")
    immunization = fields.Html("Immunization", related="customer.immunization", store=True)
    adr = fields.Html("ADRS and/or Allergies", related="customer.adr_allergy", store=True)
    diagnosis = fields.Text("Diagnosis")
    physician = fields.Char("Primary physician and contact information")

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
