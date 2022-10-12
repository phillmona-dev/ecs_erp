from odoo import models,fields

class purchase_request_link(models.Model):
    _inherit = 'droga.purhcase.request.line'
    market_analysis=fields.One2many('droga.purhcase.request.market.analysis','pr_line')
    def open_market_analysis(self):
        return {
            'name': 'Market analysis',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.purhcase.request.line',
            'view_id': self.env.ref('droga_procurement.droga_procurement_purchase_request_market_analysis').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }


#Market analysis class for purchase request
class purchase_request_market_analysis(models.Model):
    _name='droga.purhcase.request.market.analysis'
    pr_line=fields.Many2one('droga.purhcase.request.line')
    importer_name=fields.Char('Name of importer')
    manufacturer = fields.Char('Manufacturer')
    unit = fields.Many2one('uom.uom')
    avail_stock=fields.Float('Available stock')
    sell_up = fields.Float('Selling unit price')
    epss_volume = fields.Float('EPSS stock volume')
    remark=fields.Char('Remark')

class purchase_order_line_link(models.Model):
    _inherit = 'purchase.order.line'
    suppliers_list=fields.One2many('droga.purhcase.order.foreign.suppliers.list','po_line')
    competitors_comparative=fields.One2many('droga.purchase.order.foreign.competitors.comparative','po_line')

    def open_suppliers_list(self):
        return {
            'name': 'Suppliers list',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order.line',
            'view_id': self.env.ref('droga_procurement.droga_procurement_purchase_order_supp_list').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }

    def open_competitors_comparative_list(self):
        return {
            'name': 'Comparative analysis list',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order.line',
            'view_id': self.env.ref('droga_procurement.droga_procurement_purchase_order_comp_comparative').id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id,
        }

#Our foreign suppliers list for each purchase order line
class purchase_order_foreign_droga_suppliers_list(models.Model):
    _name = 'droga.purhcase.order.foreign.suppliers.list'
    po_line=fields.Many2one('purchase.order.line')
    manufacturer=fields.Many2one('res.partner','Manufacturer')
    unit_price=fields.Float('Unit price')
    shelf_life=fields.Float('Shelf life')
    is_sup_regsitered=fields.Boolean('Is supplier registered?',default=True)

#Our foreign suppliers competitors list for each purchase order line
class purhcase_order_foreign_competitors_comparative(models.Model):
    _name='droga.purchase.order.foreign.competitors.comparative'
    po_line = fields.Many2one('purchase.order.line')
    importer=fields.Char('Importer')        #Make from settings page if not highly variant
    manufacturer = fields.Char('Manufacturer')
    unit = fields.Many2one('uom.uom')
    p_up = fields.Float('Private unit price')
    p_qty = fields.Float('Private quantity')
    p_date = fields.Float('Private ordered date')
    e_u_p = fields.Float('EPSA Unit price')
    EPSA_winner = fields.Char('EPSA Winner manufacturer')
