from odoo import models, fields, api

class droga_tender_settings_customers(models.Model):
    _name = 'droga.tender.settings.customers'


    name = fields.Char("Customer Name",required=True)
    master_cust_id=fields.Many2one('res.partner')
    customer_type=fields.Many2one('droga.cust.type',string='Customer type')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)



    