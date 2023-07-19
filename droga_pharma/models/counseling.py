from email.policy import default
from odoo import models, fields, api

class droga_pharma_counselling(models.Model):
    _name = 'droga.pharma.counselling'

    #Text fields
    area_counsel=fields.Many2one('droga.pharma.area_counsel',string='Area of counselling')
    status=fields.Char("Status")
    ses_acceptance= fields.Selection([('Accepted', 'Accepted'), ('Rejected', 'Rejected')],string="Acceptance")
    pharmacist_lev_understanding=fields.Selection([('High', 'High'), ('Optimal', 'Optimal'),('Low', 'Low')],string='Pharmacist understanding')
    date=fields.Date('Date')
    # Related fields
    client = fields.Many2one('res.partner', related='sales_origin.partner_id')
    def _get_client_descr(self):
        return self.sales_origin.customer_emp
    customer = fields.Many2one('droga.pharma.cust.employees', default=_get_client_descr)
    client_descr = fields.Char(related='sales_origin.emp_descr')
    sales_origin = fields.Many2one('sale.order')


