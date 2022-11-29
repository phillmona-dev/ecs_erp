from odoo import models,fields,api

class droga_sales_invoice_payment(models.Model):
    _inherit = 'account.payment'

    def create(self,vals):
        res=super(droga_sales_invoice_payment, self).create(vals)
        invoice=self.env['account.move'].search([('name','=',vals[0]['ref'])])
        if len(invoice)>0:
            sp=self.env['stock.picking'].sudo().search([('origin','=',invoice[0]['invoice_origin'])])
            if len(sp)>0:
                for rec in sp:
                    if not rec.delivery_order_show:
                        rec.write({'delivery_order_show': True})
                        rec.action_assign()
        return res

