from odoo import models, fields, api


class payment_request_extension(models.Model):
    _inherit = 'droga.account.payment.request'
    tender_origin_form=fields.Many2one('droga.tender.master',readonly=True)

class inventory_request_extension(models.Model):
    _inherit = 'droga.inventory.consignment.issue'
    tender_origin_form=fields.Many2one('droga.tender.master',readonly=True)

class sale_order_extension(models.Model):
    _inherit = 'sale.order'
    tender_origin_form_tender=fields.Many2one('droga.tender.master',readonly=True)
    po_tender=fields.Many2many('purchase.order',string='Purchase order')

class sale_order_line_extension(models.Model):
    _inherit = 'sale.order.line'
    tender_origin_form_tender=fields.Many2one('droga.tender.master',related='order_id.tender_origin_form_tender')

class tender_customer_extension(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals_list):
        new_cus=super().create(vals_list)
        if 'supplier_rank' in vals_list:
            if vals_list["supplier_rank"]==0 and vals_list["is_company"]:
                prev_rec=self.env['droga.tender.settings.customers'].sudo().search([('name','=',vals_list['name'])])
                if len(prev_rec)>0:
                    for rec in prev_rec:
                        rec['master_cust_id']=new_cus.id
                        rec['customer_type']=vals_list['cust_type_ext']
                else:
                    tender_cus={
                        'name':vals_list['name'],
                        'master_cust_id':new_cus.id,
                        'customer_type':vals_list['cust_type_ext']}
                    self.env['droga.tender.settings.customers'].sudo().create(tender_cus)

        return new_cus