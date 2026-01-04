from odoo import models,fields
import datetime

from odoo.tools import float_compare


class update_acc(models.Model):
    _inherit='droga.stock.valuation.layer'

    def recalculateWA(self,count=10,product=0):
        if product!=0:
            dsvals = self.env['droga.stock.valuation.layer'].search(
                [ ('account_move_line_id', '=', 7928888),('product_id','=',product)], limit=count)
        else:
            dsvals=self.env['droga.stock.valuation.layer'].search([('account_move_line_id','=',7928888)],limit=count)
        for dsval in dsvals:
            #update droga_stock_valuation_layer set account_move_line_id =7928888 where company_id =2 and id in (); ot jump start
            if dsval.account_move_line_id:
                dsval.account_move_line_id = False

                dsval.revaluate_after_date(dsval,reference=dsval.origin)






    #update droga_stock_valuation_layer set po_rate=1.01,move_type='Static',description =(select (m.price_unit*m.product_qty)/case m.product_uom_qty when 0 then 1 else m.product_uom_qty end
    #from purchase_order_line m where m.id=
    #(select u.purchase_line_id from stock_move u where u.id=droga_stock_valuation_layer.stock_move_id)) where (unit_cost-(select (m.price_unit*m.product_qty)/case m.product_uom_qty when 0 then 1 else m.product_uom_qty end
    #from purchase_order_line m where m.id=
    #(select u.purchase_line_id from stock_move u where u.id=droga_stock_valuation_layer.stock_move_id)))>0.2 and origin like 'PO%' and origin not like 'PO-DF%'
    #and move_date>'2024-07-07 00:00:00.000';

    #Run this after running above query, for updating price discrepancy values
    # def update_po_entries(self):
    #     dsvals=self.env['droga.stock.valuation.layer'].search([('id','=',572563),('po_rate','=',1.01)],limit=1)
    #     for dsval in dsvals:
    #         dsval.po_rate=1
    #         if float_compare(dsval.unit_cost, float(dsval.description), precision_digits=2) != 0:
    #             new_up=float(dsval.description)
    #             dsval.InsertHistory(dsval.origin,
    #                                 dsval.quantity * new_up)
    #             dsval.unit_cost=new_up
    #             dsval.value = dsval.unit_cost * dsval.quantity
    #             dsval.fetch_and_update(dsval, reference=dsval.origin)
    #             dsval.revaluate_after_date_upd_ledger(reference=dsval.origin)


    #update droga_stock_valuation_layer set grn_rate=1.01,quantity=(select i.quantity_done from stock_move i where i.id=stock_move_id) where ...
    #Run this method after running above query, for updating quantity discrepancy values
    # def update_grn_entries(self):
    #     dsvals=self.env['droga.stock.valuation.layer'].search([('grn_rate','=',1.01)],limit=1)
    #     for dsval in dsvals:
    #         dsval.grn_rate=1
    #
    #         dsval.value = dsval.unit_cost * dsval.quantity
    #         dsval.fetch_and_update(dsval, reference=dsval.origin)
    #         dsval.revaluate_after_date_upd_ledger(reference=dsval.origin)

    # def update_acc(self):
    #     #date_limit = datetime.date(2023, 7, 7)
    #     #recs=self.env['droga.stock.valuation.layer'].search([('move_date','<',date_limit),('product_id.product_tmpl_id.categ_id','!=',40),('stock_move_id','!=',False),('inv_acc','=',False)],limit=20000)
    #     recs = self.env['droga.stock.valuation.layer'].search(
    #         [ ('product_id.product_tmpl_id.categ_id','!=',40),('company_id','=',1),('stock_move_id', '!=', False), ('inv_acc', '=', False)], limit=30000)
    #     for rec in recs:
    #
    #         if rec.stock_move_id.location_id.usage == 'supplier' and rec.stock_move_id.location_dest_id.usage != 'customer':
    #             rec.move_type = 'Static'
    #         else:
    #             rec.move_type = 'Weighted'
    #
    #         accounts = rec.product_id.product_tmpl_id.get_product_accounts()
    #         rec.inv_acc = accounts['stock_valuation']
    #
    #         am_vals = []
    #
    #         journal_id, acc_src, acc_dest, acc_valuation = rec.stock_move_id._get_accounting_data_for_valuation()
    #         # Create Journal Entry for products arriving in the company; in case of routes making the link between several
    #         # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
    #         if rec.stock_move_id._is_in():
    #             if rec.stock_move_id._is_returned(valued_type='in'):
    #                 rec.con_acc=acc_dest
    #
    #             else:
    #                 rec.con_acc = acc_src
    #
    #         # Create Journal Entry for products leaving the company
    #         if rec.stock_move_id._is_out():
    #
    #             if rec.stock_move_id._is_returned(valued_type='out'):
    #                 rec.con_acc = acc_src
    #
    #             else:
    #                 rec.con_acc = acc_dest
    #
    def post_trans(self):
        date_limit = datetime.date(2024, 7, 7)
        moves = self.env['droga.stock.valuation.layer'].search([('move_date', '>', date_limit),(), ('company_id','=',2),('value','!=',0),('account_move_id', '=', False)], limit=1000)
        for ret in moves:
            ret._validate_accounting_entries_custom()
            for svl in ret:
                svl.stock_move_id._account_analytic_entry_move()
