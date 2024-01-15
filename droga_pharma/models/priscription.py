from datetime import datetime
import pdfkit
from odoo import models, fields, api


class droga_pharma_priscription(models.Model):
    _name='droga.pharma.priscription'

    code = fields.Char("File Number", default=lambda self: self.env['ir.sequence'].next_by_code('droga.pharma.prescription.sequence'), readonly=True)
    institution = fields.Char("Institution name")
    tel = fields.Char('Tel. no')
    client = fields.Many2one('res.partner')
    age = fields.Integer("Age", compute="_compute_age")
    gender = fields.Selection(selection=[("Male", "Male"), ("Female", "Female")], string="Gender", store=True,
                              compute='get_cust_hist', inverse='update_gender')
    weight = fields.Float("Weight")
    dob = fields.Date("Date of Birth", store=True,compute='get_cust_hist',inverse='update_dob')
    patient_fullname = fields.Char("Patient's Full name", compute='_compute_fullname')
    card_no = fields.Char("Card no")
    region = fields.Char("Region")
    town = fields.Char("Town")
    wereda = fields.Char("Wereda")
    kebele = fields.Char("Kebele")
    house_no = fields.Char("House No")
    mobile = fields.Char("Mobile", related='client.mobile', store=True)
    inpatient = fields.Boolean("Inpatient")
    outpatient = fields.Boolean("Outpatient")
    diagnosis = fields.Text("Diagnosis, if not ICD")
    prescription_drugs = fields.One2many('droga.pharma.priscription.meds', 'parent_prescription')
    company_id = fields.Many2one("res.company")

    @api.depends('client')
    def _compute_fullname(self):
        for rec in self:
            rec.patient_fullname = rec.client.name

    def get_cust_hist(self):
        for rec in self:
            rec.dob = rec.client.dob
            rec.gender = rec.client.gender

    def update_dob(self):
        for rec in self:
            rec.client.dob=rec.dob

    def update_gender(self):
        for rec in self:
            rec.client.gender=rec.gender

    @api.depends("dob")
    def _compute_age(self):
        for record in self:
            if record.dob:
                record.age = datetime.now().year - record.dob.year
            else:
                record.age = 0

class droga_pharma_priscription_meds(models.Model):
    _name='droga.pharma.priscription.meds'

    drug = fields.Text("Drug description")
    price = fields.Float("Price")
    parent_prescription = fields.Many2one('droga.pharma.priscription')