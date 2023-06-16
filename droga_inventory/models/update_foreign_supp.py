from odoo import models,fields,api


class update_foreign(models.Model):
    _name = "update.foreign"

    def update_suppliers(self):
        supp=self.env['purchase.order'].search([('request_type','=','Foregin')]).mapped('partner_id')
        for partner in supp:
            partner.write({'property_stock_supplier': 263})
