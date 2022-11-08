from odoo import models,fields

class payment_request_extension(models.Model):
    _inherit = 'droga.account.payment.request'
    tender_origin_form=fields.Many2one('droga.tender.master',readonly=True)

class inventory_request_extension(models.Model):
    _inherit = 'droga.inventory.consignment.issue'
    tender_origin_form=fields.Many2one('droga.tender.master',readonly=True)

class sale_order_extension(models.Model):
    _inherit = 'sale.order'
    tender_origin_form=fields.Many2one('droga.tender.master',readonly=True)