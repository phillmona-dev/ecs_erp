from odoo import fields, models, api
from datetime import datetime, timedelta, date
#from playwright.sync_api import sync_playwright


class update_cost(models.Model):
    _name = "update.cost"

    def fetch_and_create_currency(self):
        Product = self.env['product.product']
        move_vals_list=[]
        in_stock_valuation_layers=self.env['stock.valuation.layer'].search([('stock_move_id','!=',False),('description','not like','OB%'),('description','not like','Product%'),('quantity','>',0)])
        move_vals_list += Product._svl_replenish_stock_am(in_stock_valuation_layers)
        in_stock_valuation_layers = self.env['stock.valuation.layer'].search([('stock_move_id','!=',False),('description','not like','OB%'),('description','not like','Product%'),('quantity','<',0)])
        move_vals_list += Product._svl_empty_stock_am(in_stock_valuation_layers)

        if move_vals_list:
            account_moves = self.env['account.move'].sudo().create(move_vals_list)
            account_moves._post()


