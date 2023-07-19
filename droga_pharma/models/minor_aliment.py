from email.policy import default
from odoo import models, fields, api

class droga_pharma_minor_alignment(models.Model):
    _name = 'droga.pharma.minor.alignment'

    #Text fields
    minor_align=fields.Char("Minor aliment",required=True)
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
