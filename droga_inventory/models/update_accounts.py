from odoo import models,fields
import datetime
class update_acc(models.Model):
    _inherit='droga.stock.valuation.layer'

    def update_acc(self):
        #date_limit = datetime.date(2023, 7, 7)
        #recs=self.env['droga.stock.valuation.layer'].search([('move_date','<',date_limit),('product_id.product_tmpl_id.categ_id','!=',40),('stock_move_id','!=',False),('inv_acc','=',False)],limit=20000)
        recs = self.env['droga.stock.valuation.layer'].search(
            [ ('product_id.product_tmpl_id.categ_id','!=',40),('company_id','=',1),('stock_move_id', '!=', False), ('inv_acc', '=', False)], limit=30000)
        for rec in recs:

            if rec.stock_move_id.location_id.usage == 'supplier' and rec.stock_move_id.location_dest_id.usage != 'customer':
                rec.move_type = 'Static'
            else:
                rec.move_type = 'Weighted'

            accounts = rec.product_id.product_tmpl_id.get_product_accounts()
            rec.inv_acc = accounts['stock_valuation']

            am_vals = []

            journal_id, acc_src, acc_dest, acc_valuation = rec.stock_move_id._get_accounting_data_for_valuation()
            # Create Journal Entry for products arriving in the company; in case of routes making the link between several
            # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
            if rec.stock_move_id._is_in():
                if rec.stock_move_id._is_returned(valued_type='in'):
                    rec.con_acc=acc_dest

                else:
                    rec.con_acc = acc_src

            # Create Journal Entry for products leaving the company
            if rec.stock_move_id._is_out():

                if rec.stock_move_id._is_returned(valued_type='out'):
                    rec.con_acc = acc_src

                else:
                    rec.con_acc = acc_dest

    def post_trans(self):
        date_limit = datetime.date(2024, 7, 7)
        moves = self.env['droga.stock.valuation.layer'].search([('move_date', '>', date_limit), ('company_id','=',1),('account_move_id', '=', False)], limit=1000)
        #moves = self.env['droga.stock.valuation.layer'].search(
        #    [('id','=',296275)], limit=100)
        for ret in moves:
            ret._validate_accounting_entries_custom()
            for svl in ret:
                svl.stock_move_id._account_analytic_entry_move()