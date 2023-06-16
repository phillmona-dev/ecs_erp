from odoo import models,fields,api


class update_foreign(models.Model):
    _name = "update.foreign"

    def update_suppliers(self):
        supp=self.env['purchase.order'].search([('request_type','=','Foregin')]).mapped('partner_id')
        for partner in supp:
            partner.write({'property_stock_supplier': 263})
    def update_ledger(self):
        supp = self.env['purchase.order'].search([('request_type', '=', 'Foregin')]).mapped('partner_id')
        acc_moves=self.env['account.move.line'].search([('partner_id','in',supp.ids),('account_id','=',2468),('company_id','=',1)])
        for mv in acc_moves:
            mv.write({'account_id':990})
