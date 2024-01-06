from datetime import datetime
from email.policy import default
from odoo import models, fields, api

class droga_pharma_counselling(models.Model):
    _name = 'droga.pharma.counselling'

    #Text fields
    # area_counsel=fields.Many2one('droga.pharma.area_counsel',string='Area of counselling')
    counselling_cat = fields.Selection(selection=[('life_style', 'Life style'), ('medication_use', 'Medication Use')], string='Area of counselling')
    description = fields.Char("Area of counselling description")
    status=fields.Char("Status")
    ses_acceptance= fields.Selection([('Accepted', 'Accepted'), ('Rejected', 'Rejected')],string="Acceptance")
    pharmacist_lev_understanding=fields.Selection([('High', 'High'), ('Optimal', 'Optimal'),('Low', 'Low')],string='Pharmacist level of understanding')
    assessment = fields.Html("Assessment")
    date=fields.Date('Date')
    sales_origin = fields.Many2one('sale.order')
    counselling_given = fields.Html("Counselling given")
    patient_lev_understanding=fields.Selection([('High', 'High'), ('Optimal', 'Optimal'),('Low', 'Low')],string='Patient Level of understanding')
    # Related fields
    client = fields.Many2one('res.partner')
    client_descr = fields.Char(related='sales_origin.emp_descr')
    customer = fields.Many2one('droga.pharma.cust.employees', related='sales_origin.customer_emp')
    mobile = fields.Char("Mobile", related='client.phone', store=True)
    medical = fields.Html("Medical History", store=True)
    medication_history = fields.Html("Medication History and adherence", store=True)
    dob = fields.Date("Date of Birth", store=True)
    age = fields.Integer("Age", compute="_compute_age", readonly=True)
    gender = fields.Selection(selection=[("Male", "Male"), ("Female", "Female")], string="Gender", store=True)
    profession = fields.Selection(selection=[("hp", "Health Professional"), ("other", "Other")], string="Profession", store=True)
    weight = fields.Float("Weight")
    height = fields.Float("Height")
    bsa = fields.Float("BSA")
    address = fields.Char("Address")
    pregnancy = fields.Boolean("Pregnancy status")
    immunization = fields.Html("Immunization", store=True)
    adr = fields.Html("ADRS and/or Allergies", store=True)
    diagnosis = fields.Text("Diagnosis")
    physician = fields.Char("Primary physician and contact information")

    @api.depends("dob")
    def _compute_age(self):
        for record in self:
            if record.dob:
                record.age = datetime.now().year - record.dob.year
            else:
                record.age = 0
