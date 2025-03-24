from email.policy import default
from collections import defaultdict
from odoo import api, fields, models, tools,_
from odoo.tools import float_compare, float_is_zero
from odoo.exceptions import UserError

class StockValuationLayerInherit(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model
    def create(self, vals):
        ret = super(StockValuationLayerInherit, self).create(vals)

        dsvl = {
            'svl_id': ret.id,
            'company_id': ret.company_id.id,
            'product_id': ret.product_id.id,
            'quantity': ret.quantity,
            'unit_cost': ret.unit_cost if not ret.stock_move_id.purchase_line_id else ret.unit_cost*ret.stock_move_id.purchase_line_id.order_id.cost_rate,
            'value': ret.value if not ret.stock_move_id.purchase_line_id else ret.value * ret.stock_move_id.purchase_line_id.order_id.cost_rate,
            'description': ret.description,
            'stock_move_id': ret.stock_move_id.id,
            'account_move_line_id': ret.account_move_line_id.id,
            # Check below field
            'move_date': ret.create_date
        }

        self.env['droga.stock.valuation.layer'].sudo().create(dsvl)
        return ret


class DrogaStockValuationLayer(models.Model):
    _name = 'droga.stock.valuation.layer'
    _description = 'Stock Valuation Layer'
    _order = 'product_id,move_date,move_type, id'

    _rec_name = 'product_id'

    company_id = fields.Many2one('res.company', 'Company', readonly=True, required=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, required=True)
    categ_id = fields.Many2one('product.category', related='product_id.categ_id')
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    quantity = fields.Float('Quantity', readonly=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one(related='product_id.uom_id', readonly=True, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True,
                                  required=True)
    unit_cost = fields.Monetary('Unit Value', readonly=True)
    value = fields.Monetary('Total Value', readonly=True)
    remaining_qty = fields.Float(readonly=True, digits='Product Unit of Measure')
    remaining_value = fields.Monetary('Remaining Value', readonly=True)
    description = fields.Char('Description', readonly=True)
    stock_move_id = fields.Many2one('stock.move', 'Stock Move', readonly=True, index=True)
    account_move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True, index="btree_not_null")
    account_move_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True, index="btree_not_null")
    reference = fields.Char(related='stock_move_id.reference')
    inv_acc = fields.Many2one('account.account', string='Inventory account')
    con_acc = fields.Many2one('account.account', string='Contra account')
    svl_id = fields.Integer('SVL ID')
    move_date = fields.Date('Move date', required=True)
    origin = fields.Char(related='stock_move_id.origin', store=True)
    move_type = fields.Selection([
        ('Static', 'Static'),
        ('Weighted', 'Weighted'),
    ], string='Move type',
        help='Static types are transactions that we receive from suppliers and they change our weighted average price. Weighted types are '
             'types of transactions where we have to calculate weighted average value.')

    @api.model
    def create(self, vals):
        ret = super(DrogaStockValuationLayer, self).create(vals)

        if ret.stock_move_id.location_id.usage == 'supplier' and ret.stock_move_id.location_dest_id.usage!='customer':
            ret.move_type = 'Static'
        else:
            ret.move_type = 'Weighted'

        prior_trans = self.get_parent_id(ret.product_id.id, ret.move_date, ret.move_type, ret.svl_id)

        if prior_trans:
            self.update_trans(prior_trans, ret)
        else:
            # There are no prior transactions
            ret.remaining_value = ret.value
            ret.remaining_qty = ret.quantity

        accounts = ret.product_id.product_tmpl_id.get_product_accounts()
        ret.inv_acc = accounts['stock_valuation']

        # ret._validate_accounting_entries_custom()
        # for svl in self:
        #     svl.stock_move_id._account_analytic_entry_move()

        self.revaluate_after_date(ret)

        return ret

    def _validate_accounting_entries_custom(self):
        am_vals = []
        for svl in self:
            if not svl.with_company(svl.company_id).product_id.valuation == 'custom_posting':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            move = svl.stock_move_id
            if not move:
                move = svl.stock_valuation_layer_id.stock_move_id
            am_vals += move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
        for val in am_vals:
            self.con_acc=val['line_ids'][0][2]['account_id'] if val['line_ids'][0][2]['account_id']!=self.inv_acc.id else val['line_ids'][1][2]['account_id']
        if am_vals:
            account_moves = self.env['account.move'].sudo().create(am_vals)
            account_moves._post()
            self.account_move_id=account_moves.id

    def revaluate_after_date(self,ret):
        trans_after = self.get_trans_after(ret.product_id.id, ret.move_date, ret.move_type, ret.svl_id)
        init_trans = ret
        for trans in trans_after:
            self.update_trans(init_trans, trans,post_diff=True)
            init_trans = trans

    # This function takes 2 objects of valuation layer and updates the current row based on the previous row values.
    def update_trans(self, prev_trans, cur_trans,post_diff=False):
        if cur_trans.move_type == 'Static':
            cur_trans.remaining_value = cur_trans.value + prev_trans.remaining_value
            cur_trans.remaining_qty = cur_trans.quantity + prev_trans.remaining_qty
        else:
            old_value=cur_trans.value
            cur_trans.unit_cost = (abs(prev_trans.remaining_value) / abs(
                prev_trans.remaining_qty)) if prev_trans.remaining_qty != 0 else (
                    abs(prev_trans.value) / abs(prev_trans.quantity))
            cur_trans.value = cur_trans.quantity * cur_trans.unit_cost
            cur_trans.remaining_value = cur_trans.value + prev_trans.remaining_value
            cur_trans.remaining_qty = cur_trans.quantity + prev_trans.remaining_qty

            if float_compare(old_value,cur_trans.value,precision_digits=2) !=0:
                if cur_trans.account_move_id:

                    #write a query to update
                    query1="""
                        update account_move set amount_total=%s,amount_total_signed=%s,amount_total_in_currency_signed=%s,core_amt=case core_amt when 0 then 0 else %s end,non_core_amt=
                        case non_core_amt when 0 then 0 else %s end where id=%s
                    """
                    self.env.cr.execute(query1, (abs(cur_trans.value),abs(cur_trans.value),abs(cur_trans.value),abs(cur_trans.value),abs(cur_trans.value),cur_trans.account_move_id.id))

                    query2 = """
                                            update account_move_line set debit= case when debit=0 then 0 else %s end,credit=case when credit=0 then 0 else %s end,
                                            balance=case when balance=0 then 0 else (balance/abs(balance))*%s end,amount_currency=case when amount_currency=0 then 0 else (amount_currency/abs(amount_currency))*%s end
                                            where move_id=%s
                                        """
                    self.env.cr.execute(query2, (
                    abs(cur_trans.value), abs(cur_trans.value), abs(cur_trans.value),
                    abs(cur_trans.value), cur_trans.account_move_id.id))

    # Gets initial row value for processing start
    def get_parent_id(self, prod_id, trans_date, trans_type, cur_id):
        if trans_type == 'Static':
            to_ret = self.env['droga.stock.valuation.layer'].search(
                ["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", "<", trans_date), "&", ("move_date", "=", trans_date), "&",
                 ("svl_id", "!=", cur_id), ("move_type", "=", "Static")],
                order="move_date desc, move_type desc, svl_id desc", limit=1)
            return to_ret if to_ret else False
        else:
            to_ret = self.env['droga.stock.valuation.layer'].search(["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", "<", trans_date),
                                                                     "|", "&", ("move_date", "=", trans_date), "&", ("svl_id", "<", cur_id), ("move_type", "=", "Weighted"),
                                                                     "&", ("move_date", "=", trans_date), ("move_type", "=", "Static")],
                                                                    order="move_date desc, move_type desc, svl_id desc",limit=1)
            return to_ret if to_ret else False

    def get_trans_after(self, prod_id, trans_date, trans_type, cur_id):
        if trans_type == 'Static':
            to_ret = self.env['droga.stock.valuation.layer'].search(
                ["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", ">", trans_date), "|", "&", ("move_date", "=", trans_date),
                 ("move_type", "=", "Weighted"), "&", ("move_date", "=", trans_date), "&", ("move_type", "=", "Static"), ("svl_id", ">", cur_id)],
                order="move_date asc, move_type asc, svl_id asc")
            return to_ret if to_ret else []
        else:
            to_ret = self.env['droga.stock.valuation.layer'].search(
                ["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", ">", trans_date), "&", ("move_date", "=", trans_date), "&",
                 ("move_type", "=", "Weighted"), ("svl_id", ">", cur_id)],
                order="move_date asc, move_type asc, svl_id asc")
            return to_ret if to_ret else []

class DrogaLandedCost(models.Model):
    _inherit='stock.landed.cost'
    target_model = fields.Selection(selection_add=[
        ('pos', 'Purchase orders')
    ],ondelete={'pos': 'set default'},default='pos')
    purchase_orders=fields.Many2many(
        'purchase.order', string='Purchase orders',
        copy=False, states={'done': [('readonly', True)]})
    purchase_total=fields.Float('Purchase total',compute='get_purch_total')
    lc_rate=fields.Float('Landed Cost Rate',digits=(16, 8))

    @api.depends('purchase_orders')
    def get_purch_total(self):
        for rec in self:
            rec.purchase_total=0
            for po in rec.purchase_orders:
                rec.purchase_total=rec.purchase_total+po.amount_total
            rec.lc_rate=((rec.amount_total+rec.purchase_total)/rec.purchase_total) if rec.purchase_total else 1

    def button_validate(self):
        if any(cost.target_model != 'pos' for cost in self):
            return super(DrogaLandedCost, self).button_validate()
        else:
            #For all receipts, update cost here
            for res in self:

                for po in res.purchase_orders:
                    po_rate = 1

                    for rate in self.env['stock.landed.cost'].search(
                            [('purchase_orders', 'in', po.id), ('state', '=', 'done')]):
                        po_rate = po_rate + (rate['lc_rate'] - 1)
                    po_rate=po_rate + (res.lc_rate-1)
                    #Get stock move ids
                    move_ids=self.env['stock.move'].search([('purchase_line_id','in',po.order_line.ids)]).ids
                    #Get valuation layers
                    for val in self.env['droga.stock.valuation.layer'].search([('stock_move_id','in',move_ids)]):

                        #Check if existing unit cost is different from purchase unit cost *
                        if float_compare(val.unit_cost, val.stock_move_id.purchase_line_id.price_unit*po_rate, precision_digits=3) != 0:
                            val.unit_cost=val.stock_move_id.purchase_line_id.price_unit*po_rate
                            val.remaining_value=val.remaining_value + ((val.quantity * val.unit_cost)- val.value)
                            val.value=val.quantity * val.unit_cost
                            val.revaluate_after_date(val)
                res.state='done'
            return True

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    cost_rate=fields.Float('Cost Rate',default=1,compute='get_cost_rate')

    def get_cost_rate(self):
        for rec in self:
            po_rate=1
            for rate in self.env['stock.landed.cost'].search(
                    [('purchase_orders', 'in', rec.id), ('state', '=', 'done')]):
                po_rate = po_rate + (rate['lc_rate'] - 1)
            rec.cost_rate=po_rate

class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_valuation = fields.Selection(selection_add=[
        ('custom_posting', 'Custom Posting')
    ],company_dependent=True, copy=True, required=True,ondelete={'custom_posting': 'set default'})