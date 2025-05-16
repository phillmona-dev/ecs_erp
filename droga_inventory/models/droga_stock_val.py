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
        if ret.quantity!=0:
            dsvl = {
                'svl_id': ret.id,
                'company_id': ret.company_id.id,
                'product_id': ret.product_id.id,
                'quantity': ret.quantity,
                'unit_cost': ret.unit_cost if not ret.stock_move_id.purchase_line_id else ret.unit_cost*ret.stock_move_id.purchase_line_id.order_id.cost_rate,
                'value': ret.value if not ret.stock_move_id.purchase_line_id else ret.value * ret.stock_move_id.purchase_line_id.order_id.cost_rate,
                'description': ret.description,
                'po_rate':1 if not ret.stock_move_id.purchase_line_id else ret.stock_move_id.purchase_line_id.order_id.cost_rate,
                'stock_move_id': ret.stock_move_id.id,
                'account_move_line_id': ret.account_move_line_id.id,
                # Check below field
                'move_date': ret.create_date,
                'move_date_initial': ret.create_date,
                'move_type':'Weighted'
            }

            self.env['droga.stock.valuation.layer'].sudo().create(dsvl)
        return ret

class DrogaStockValuationHistory(models.Model):
    _name='droga.stock.valuation.history'
    dsvl_id=fields.Many2one('droga.stock.valuation.layer')
    quantity = fields.Float('Quantity')
    unit_cost = fields.Float('Unit Value')
    reference=fields.Char('Reference')
    value = fields.Float('Total Value')
    to_value = fields.Float('To Value')
    remaining_qty = fields.Float('Remaining Quantity')
    remaining_value = fields.Float('Remaining Value')
    upd_date=fields.Datetime('Update date')

class DrogaStockValuationLayer(models.Model):
    _name = 'droga.stock.valuation.layer'
    _description = 'Droga Stock Valuation Layer'
    _order = 'product_id,move_date,move_type, id'

    _rec_name = 'product_id'

    history_vals=fields.One2many('droga.stock.valuation.history','dsvl_id')
    company_id = fields.Many2one('res.company', 'Company', readonly=True, required=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, required=True)
    categ_id = fields.Many2one('product.category',string='Product category',related='product_id.categ_id',store=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    quantity = fields.Float('Quantity', readonly=True, digits='Product Unit of Measure')
    uom_id = fields.Many2one(related='product_id.uom_id', readonly=True, required=True)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True,
                                  required=True)
    unit_cost = fields.Float('Unit Value', readonly=True)
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
    move_date_initial = fields.Date('Move date origin', required=True)
    origin = fields.Char(related='stock_move_id.origin', store=True)
    po_rate=fields.Float('PO Rate',default=1,store=True)
    grn_rate = fields.Float('GRN Rate', default=1, store=True)
    move_type = fields.Selection([
        ('Static', 'Static'),
        ('Weighted', 'Weighted'),
    ], string='Move type',
        help='Static types are transactions that we receive from suppliers and they change our weighted average price. Weighted types are '
             'types of transactions where we have to calculate weighted average value.')
    remark=fields.Char('Remark')
    def show_history(self):
        return {
            'name': 'Valuation update history',
            'view_type': 'tree',
            'view_mode': 'tree',
            'res_model': 'droga.stock.valuation.history',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain':
                ([('dsvl_id', '=', self.id)])
        }

    def InsertHistory(self,ref,to_value):
        for rec in self:
            dsval  = {
                        'dsvl_id': rec.id,
                        'reference':ref,
                        'quantity':rec.quantity,
                        'unit_cost': rec.unit_cost,
                        'value': rec.value,
                        'to_value': to_value,
                        'remaining_qty': rec.remaining_qty,
                        'remaining_value': rec.remaining_value,
                        'upd_date':fields.datetime.now()
                    }

            rec.env['droga.stock.valuation.history'].create(dsval)

    def fetch_and_update(self,ret,reference='-',date_change=False):
        prior_trans = self.get_parent_id(ret.product_id.id, ret.move_date, ret.move_type, ret.svl_id)

        if prior_trans:
            self.update_trans(prior_trans, ret, reference=reference,date_change=date_change)
        else:
            # There are no prior transactions
            ret.remaining_value = ret.value if ret.value>0 else 0
            ret.remaining_qty = ret.quantity if ret.quantity>0 else 0
            ret.remark=''

    @api.model
    def create(self, vals):
        ret = super(DrogaStockValuationLayer, self).create(vals)

        self.update_wa_after_date(ret)

        return ret

    def update_wa_after_date(self,ret):
        if ret.stock_move_id.location_id.con_type == 'SUBL' or ret.stock_move_id.location_id.con_type == 'CONR' or (
                ret.stock_move_id.location_id.usage == 'supplier' and ret.stock_move_id.location_dest_id.usage != 'customer') or (
                ret.stock_move_id.location_dest_id.usage == 'supplier' and ret.stock_move_id.location_id.usage != 'customer'):
            ret.move_type = 'Static'
            if ret.stock_move_id.location_dest_id.usage == 'supplier' and ret.stock_move_id.origin_returned_move_id:
                unit_cost = self.env['droga.stock.valuation.layer'].search(
                    [('move_type', '=', 'Static'), ('stock_move_id', '=', ret.stock_move_id.origin_returned_move_id.id)],
                    limit=1)
                if unit_cost:  # If there's no static valuation, we'll treat it as weighted transaction as well
                    if unit_cost[
                        'move_date'] > ret.company_id.tax_lock_date:  # Make sure period is not closed for the date, if closed we'll treat it as weighted transaction
                        ret.unit_cost = unit_cost['unit_cost']
                        ret.value = ret.unit_cost * ret.quantity
                        # ret.move_date=unit_cost['move_date']
                else:
                    ret.move_type = 'Weighted'
        else:
            ret.move_type = 'Weighted'

        self.fetch_and_update(ret)

        accounts = ret.product_id.product_tmpl_id.get_product_accounts()
        ret.inv_acc = accounts['stock_valuation']

        ret._validate_accounting_entries_custom()
        for svl in ret:
            svl.stock_move_id._account_analytic_entry_move()

        self.revaluate_after_date(ret)

        self.updatesalescost(ret)

    def updatesalescost(self,ret):
        # This updates sales cost value for sales transactions. Out refund is sales return
        if ret.origin:
            if ret.origin.startswith('SO'):
                acc_move = self.env['account.move'].search([('invoice_origin', '=', ret.origin)])
                for mv in acc_move:
                    mvl = mv.line_ids
                    for mvld in mvl:

                        stock_move_ids=self.env['stock.move'].search([('sale_line_id','in',mvld.sale_line_ids.ids)])

                        val_layers=self.env['droga.stock.valuation.layer'].search([('stock_move_id','in',stock_move_ids.ids)])
                        if len(val_layers)==0:
                            mvld.sales_cost=0
                        else:
                            mvld.sales_cost = sum(val_layers.mapped('value'))

                    mv.sales_cost = sum(mv.line_ids.mapeed('sales_cost'))

    def _validate_accounting_entries_custom(self):
        accounts = self.product_id.product_tmpl_id.get_product_accounts()
        self.inv_acc = accounts['stock_valuation']

        am_vals = []
        for svl in self:
            if not svl.with_company(svl.company_id).product_id.valuation == 'custom_posting':
                continue
            if svl.currency_id.is_zero(svl.value):
                continue
            move = svl.stock_move_id
            if not move:
                move = svl.stock_valuation_layer_id.stock_move_id
            am_vals += move.with_company(svl.company_id)._account_entry_move_custom(svl.quantity, svl.description, svl.id, svl.value)
        for val in am_vals:
            self.con_acc=val['line_ids'][0][2]['account_id'] if val['line_ids'][0][2]['account_id']!=self.inv_acc.id else val['line_ids'][1][2]['account_id']
        if am_vals:
            account_moves = self.env['account.move'].sudo().create(am_vals)
            account_moves['invoice_origin']=self.origin
            account_moves._post()

            self.account_move_id=account_moves.id

    def revaluate_after_date_upd_ledger(self,reference=''):
        ret=self
        if ret.account_move_id:
            query1 = """
                                    update account_move set amount_total=%s,amount_total_signed=%s,amount_total_in_currency_signed=%s,core_amt=case core_amt when 0 then 0 else %s end,non_core_amt=
                                    case non_core_amt when 0 then 0 else %s end where id=%s
                                """
            self.env.cr.execute(query1, (
            abs(ret.value), abs(ret.value), abs(ret.value), abs(ret.value), abs(ret.value),
            ret.account_move_id.id))

            query2 = """
                                                update account_move_line set 
                                                debit= case when ((account_id=%s and %s > 0) or (account_id!=%s and %s < 0)) then %s else 0 end,
                                                credit= case when ((account_id=%s and %s < 0) or (account_id!=%s and %s > 0)) then %s else 0 end,
                                                balance=case when ((account_id=%s and %s > 0) or (account_id!=%s and %s < 0)) then %s else -1 * %s end,
                                                amount_currency=case when ((account_id=%s and %s > 0) or (account_id!=%s and %s < 0)) then %s else -1 * %s end
                                                where move_id=%s
                                            """
            self.env.cr.execute(query2, (ret.inv_acc.id, ret.value,ret.inv_acc.id, ret.value, abs(ret.value),
                                         ret.inv_acc.id, ret.value,ret.inv_acc.id, ret.value, abs(ret.value),
                                         ret.inv_acc.id, ret.value,ret.inv_acc.id, ret.value, abs(ret.value),abs(ret.value),
                                         ret.inv_acc.id, ret.value,ret.inv_acc.id, ret.value, abs(ret.value),abs(ret.value),
                                         ret.account_move_id.id))

        self.updatesalescost(ret)

        self.revaluate_after_date(ret,reference=reference)
        # trans_after = self.get_trans_after(ret.product_id.id, ret.move_date, ret.move_type, ret.svl_id)
        # init_trans = ret
        # for trans in trans_after:
        #     self.update_trans(init_trans, trans,reference=reference)
        #     init_trans = trans

    def revaluate_after_date(self,ret,reference='-'):
        trans_after = self.get_trans_after(ret.product_id.id, ret.move_date, ret.move_type, ret.svl_id)
        init_trans = ret
        for trans in trans_after:
            ret_val=self.update_trans(init_trans, trans,reference=reference)
            init_trans = trans
            if not ret_val:
                break

    # This function takes 2 objects of valuation layer and updates the current row based on the previous row values.
    def update_trans(self, prev_trans, cur_trans,reference='-',date_change=False):
        old_value = cur_trans.value
        if cur_trans.move_type == 'Static':
            if cur_trans.origin and cur_trans.quantity < 0:
                if cur_trans.origin.startswith('P'):
                    unit_cost = self.env['droga.stock.valuation.layer'].search([('move_type', '=', 'Static'),
                                                                                ('stock_move_id', '=',
                                                                                 cur_trans.stock_move_id.origin_returned_move_id.id)],
                                                                               limit=1)
                    if unit_cost:
                        cur_trans.unit_cost=unit_cost['unit_cost']
                        cur_trans.value=cur_trans.unit_cost*cur_trans.quantity

                        if float_compare(old_value, cur_trans.value, precision_digits=2) != 0:
                            self.update_gl(cur_trans)

            #In case it's a purchase return and the remaining quantity becomes 0, we use the remaining value to balance it
            if cur_trans.quantity<0 and (prev_trans.remaining_qty+cur_trans.quantity)==0:
                cur_trans.value=prev_trans.remaining_value*-1
                cur_trans.unit_cost=cur_trans.value/cur_trans.quantity
            if prev_trans.remaining_qty<0:
                trans_before = self.get_parent_negative_date_id(cur_trans.product_id.id, cur_trans.move_date, cur_trans.svl_id)
                if trans_before:
                    cur_trans.move_date=trans_before.move_date
                    cur_trans.fetch_and_update(cur_trans)
                    cur_trans.revaluate_after_date(cur_trans)
                    return False
                else:
                    cur_trans.remark='Negative stock, prior transaction not found'
                    cur_trans.remaining_value = cur_trans.value + prev_trans.remaining_value
                    cur_trans.remaining_qty = cur_trans.quantity + prev_trans.remaining_qty
                    return True
            else:
                cur_trans.remaining_value = cur_trans.value + prev_trans.remaining_value
                cur_trans.remaining_qty = cur_trans.quantity + prev_trans.remaining_qty

                return True
        else:

            if reference!='-' and float_compare(cur_trans.unit_cost, ((abs(prev_trans.remaining_value) / abs(
                prev_trans.remaining_qty)) if prev_trans.remaining_qty != 0 else abs(
                    prev_trans.remaining_value / cur_trans.quantity)), precision_digits=2) != 0:
                cur_trans.InsertHistory(reference,cur_trans.quantity * ((abs(prev_trans.remaining_value) / abs(
                    prev_trans.remaining_qty)) if prev_trans.remaining_qty != 0 else abs(
                    prev_trans.remaining_value / cur_trans.quantity)))

            cur_trans.unit_cost = (abs(prev_trans.remaining_value) / abs(
                prev_trans.remaining_qty)) if prev_trans.remaining_qty != 0 else abs(prev_trans.unit_cost)
            cur_trans.value = cur_trans.quantity * cur_trans.unit_cost
            if cur_trans.value + prev_trans.remaining_value>=0:
                cur_trans.remaining_value = cur_trans.value + prev_trans.remaining_value
                cur_trans.remaining_qty = cur_trans.quantity + prev_trans.remaining_qty
                cur_trans.remark=''
            else:
                cur_trans.remark='Entry is negative stock. Please update date accordingly.'
                cur_trans.remaining_value = cur_trans.value + prev_trans.remaining_value
                cur_trans.remaining_qty = cur_trans.quantity + prev_trans.remaining_qty
                #Get future date, update current with future date, call wa updater for previous transaction and return false


            if float_compare(old_value,cur_trans.value,precision_digits=2) !=0:

                self.update_gl(cur_trans)

                self.updatesalescost(cur_trans)
            return True

    def update_gl(self,cur_trans):
        if cur_trans.account_move_id:
            # write a query to update
            query1 = """
                update account_move set amount_total=%s,amount_total_signed=%s,amount_total_in_currency_signed=%s,core_amt=case core_amt when 0 then 0 else %s end,non_core_amt=
                case non_core_amt when 0 then 0 else %s end where id=%s
            """
            self.env.cr.execute(query1,
                                (abs(cur_trans.value), abs(cur_trans.value), abs(cur_trans.value), abs(cur_trans.value),
                                 abs(cur_trans.value), cur_trans.account_move_id.id))

            query2 = """
                        update account_move_line set 
                        debit= case when ((account_id=%s and %s > 0) or (account_id!=%s and %s < 0)) then %s else 0 end,
                        credit= case when ((account_id=%s and %s < 0) or (account_id!=%s and %s > 0)) then %s else 0 end,
                        balance=case when ((account_id=%s and %s > 0) or (account_id!=%s and %s < 0)) then %s else -1 * %s end,
                        amount_currency=case when ((account_id=%s and %s > 0) or (account_id!=%s and %s < 0)) then %s else -1 * %s end
                        where move_id=%s
                    """
            self.env.cr.execute(query2,
                                (cur_trans.inv_acc.id, cur_trans.value, cur_trans.inv_acc.id, cur_trans.value,
                                 abs(cur_trans.value),
                                 cur_trans.inv_acc.id, cur_trans.value, cur_trans.inv_acc.id, cur_trans.value,
                                 abs(cur_trans.value),
                                 cur_trans.inv_acc.id, cur_trans.value, cur_trans.inv_acc.id, cur_trans.value,
                                 abs(cur_trans.value),
                                 abs(cur_trans.value),
                                 cur_trans.inv_acc.id, cur_trans.value, cur_trans.inv_acc.id, cur_trans.value,
                                 abs(cur_trans.value),
                                 abs(cur_trans.value),
                                 cur_trans.account_move_id.id))
    # Gets initial row value for processing start
    def get_parent_id(self, prod_id, trans_date, trans_type, cur_id):
        if trans_type == 'Static':
            to_ret = self.env['droga.stock.valuation.layer'].search(
                ["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", "<", trans_date), "&", ("move_date", "=", trans_date), "&",
                 ("svl_id", "<", cur_id), ("move_type", "=", "Static")],
                order="move_date desc, move_type desc, svl_id desc", limit=1)
            return to_ret if to_ret else False
        else:
            to_ret = self.env['droga.stock.valuation.layer'].search(["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", "<", trans_date),
                                                                     "|", "&", ("move_date", "=", trans_date), "&", ("svl_id", "<", cur_id), ("move_type", "=", "Weighted"),
                                                                     "&", ("move_date", "=", trans_date), ("move_type", "=", "Static")],
                                                                    order="move_date desc, move_type desc, svl_id desc",limit=1)
            return to_ret if to_ret else False


    def get_parent_negative_date_id(self, prod_id, trans_date, cur_id):
        to_ret = self.env['droga.stock.valuation.layer'].search(
            [("svl_id", "!=", cur_id), ("remaining_qty", "<", 0),  ("product_id", "=", prod_id), ("move_date", "<", trans_date)],
            order="move_date asc, move_type asc, quantity asc,svl_id asc", limit=1)
        return to_ret if to_ret else False

    def get_trans_after(self, prod_id, trans_date, trans_type, cur_id):
        if trans_type == 'Static':
            to_ret = self.env['droga.stock.valuation.layer'].search(
                ["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", ">", trans_date), "|", "&", ("move_date", "=", trans_date),
                 ("move_type", "=", "Weighted"), "&", ("move_date", "=", trans_date), "&", ("move_type", "=", "Static"), ("svl_id", ">", cur_id)],
                order="move_date asc, move_type asc, quantity desc,svl_id asc")
            return to_ret if to_ret else []
        else:
            to_ret = self.env['droga.stock.valuation.layer'].search(
                ["&", ("svl_id", "!=", cur_id), "&", ("product_id", "=", prod_id), "|", ("move_date", ">", trans_date), "&", ("move_date", "=", trans_date), "&",
                 ("move_type", "=", "Weighted"), ("svl_id", ">", cur_id)],
                order="move_date asc, move_type asc, quantity desc,svl_id asc")
            return to_ret if to_ret else []

class DrogaLandedCost(models.Model):
    _inherit='stock.landed.cost'
    target_model = fields.Selection(selection_add=[
        ('pos', 'Purchase orders')
    ],ondelete={'pos': 'set default'},default='pos')
    purchase_orders=fields.Many2many(
        'purchase.order', string='Purchase orders',
        copy=False, states={'done': [('readonly', True)]})
    purchase_total=fields.Float('Purchase total',compute='get_purch_grn_total',store=True)
    grn_total = fields.Float('GRN total', compute='get_purch_grn_total', store=True)
    lc_rate=fields.Float('Landed Cost Rate',digits=(16, 8))

    @api.depends('purchase_orders','picking_ids','target_model','amount_total')
    def get_purch_grn_total(self):
        for rec in self:
            rec.purchase_total=0
            rec.grn_total=0
            if rec.target_model=='pos':
                for po in rec.purchase_orders:
                    rec.purchase_total=rec.purchase_total+po.amount_total
                rec.lc_rate=((rec.amount_total+rec.purchase_total)/rec.purchase_total) if rec.purchase_total!=0 else 1
            elif rec.target_model=='picking':
                for mv in rec.picking_ids.move_ids:
                    vals=self.env['droga.stock.valuation.layer'].search([('stock_move_id','=',mv.id)])
                    for val in vals:
                        #Divide by grn_rate to get GRN amount before PO and GRN update
                        rec.grn_total=rec.grn_total+(val.value/(val.po_rate+val.grn_rate-1))
                rec.lc_rate=((rec.amount_total+rec.grn_total)/rec.grn_total) if rec.grn_total!=0 else 1

    def button_validate(self):
        if any(cost.target_model not in ('pos','picking') for cost in self):
            return super(DrogaLandedCost, self).button_validate()
        else:
            #For all receipts, update cost here
            for res in self:
                if res.target_model=='pos':
                    for po in res.purchase_orders:
                        # Get stock move ids
                        move_ids=self.env['stock.move'].search([('purchase_line_id','in',po.order_line.ids)]).ids
                        #Get valuation layers
                        for val in self.env['droga.stock.valuation.layer'].search([('stock_move_id','in',move_ids)]):
                            if res.lc_rate!=1:
                                orig_unit_cost = val.unit_cost / (val.po_rate * val.grn_rate)
                                val.po_rate += (res.lc_rate - 1)
                                val.InsertHistory(res.name,val.quantity * (orig_unit_cost * (val.po_rate + val.grn_rate - 1)))

                                val.unit_cost= orig_unit_cost*(val.po_rate+val.grn_rate-1)
                                val.remaining_value=val.remaining_value + ((val.quantity * (orig_unit_cost*(val.po_rate+val.grn_rate-1)))- val.value)
                                val.value=val.quantity * (orig_unit_cost*(val.po_rate+val.grn_rate-1))
                                val.revaluate_after_date_upd_ledger(reference=res.name)
                    res.state='done'
                else:
                    for grn in res.picking_ids:
                        # Get stock move ids
                        move_ids = grn.move_ids.ids
                        # Get valuation layers
                        for val in self.env['droga.stock.valuation.layer'].search([('stock_move_id', 'in', move_ids)]):
                            if res.lc_rate!=1:
                                orig_unit_cost=val.unit_cost/(val.po_rate*val.grn_rate)
                                val.grn_rate += (res.lc_rate - 1)
                                val.InsertHistory(res.name, val.quantity * (orig_unit_cost*(val.po_rate+val.grn_rate-1)))

                                val.unit_cost= orig_unit_cost*(val.po_rate+val.grn_rate-1)
                                val.remaining_value = val.remaining_value + ((val.quantity * (orig_unit_cost*(val.po_rate+val.grn_rate-1))) - val.value)
                                val.value = val.quantity * (orig_unit_cost*(val.po_rate+val.grn_rate-1))
                                val.revaluate_after_date_upd_ledger(reference=res.name)
                    res.state = 'done'
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

class PurchaseOrderLine(models.Model):
    _inherit='purchase.order.line'

    def write(self, vals):
        ret=super(PurchaseOrderLine, self).write(vals)
        if 'price_unit' in vals or 'product_qty' in vals:
            for rec in self:
                # for order in rec:
                for move in rec.mapped('move_ids'):
                    if move.state == 'done':
                        raise UserError(
                            _('Unable to update purchase order %s as some receptions have already been done.') % (
                                rec.order_id.name))
                if rec.state in ('purchase', 'done'):
                    moves = self.env['stock.move'].search([('purchase_line_id', '=', rec.id)])
                    for move in moves:
                        dsvals = self.env['droga.stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
                        for dsval in dsvals:
                            new_up=rec.price_unit* (rec.product_uom.factor/rec.product_id.uom_id.factor)
                            dsval.InsertHistory(dsval.origin,
                                              dsval.quantity * new_up)
                            dsval.unit_cost = new_up
                            dsval.value=dsval.unit_cost*dsval.quantity
                            dsval.fetch_and_update(dsval,reference=dsval.origin)
                            dsval.revaluate_after_date_upd_ledger(reference=dsval.origin)

                            query2 = """
                                            update account_move_line g set stat=case when (select sum(i.balance) from account_move_line i where i.inv_origin=g.inv_origin and i.account_id=g.account_id)=0 then 'Matched' else 
                                            'Unmatched' end where g.account_id in (2468,990,4221) and g.inv_origin=%s
                                        """
                            self.env.cr.execute(query2,
                                                (dsval.origin,))
        return ret

class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_valuation = fields.Selection(selection_add=[
        ('custom_posting', 'Custom Posting')
    ],company_dependent=True, copy=True, required=True,ondelete={'custom_posting': 'set default'})

class StockMovesVal(models.Model):
    _inherit='stock.move'
    def _account_entry_move_custom(self, qty, description, svl_id, cost):
        """ Accounting Valuation Entries """
        self.ensure_one()
        am_vals = []
        if self.product_id.type != 'product':
            # no stock valuation for consumable products
            return am_vals
        if self.restrict_partner_id and self.restrict_partner_id != self.company_id.partner_id:
            # if the move isn't owned by the company, we don't make any valuation
            return am_vals

        company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        # Create Journal Entry for products arriving in the company; in case of routes making the link between several
        # warehouse of the same company, the transit location belongs to this company, so we don't need to create accounting entries
        if self._is_in():
            if self._is_returned(valued_type='in'):
                am_vals.append(self.with_company(company_to).with_context(is_returned=True)._prepare_account_move_vals_custom(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost))
            else:
                am_vals.append(self.with_company(company_to)._prepare_account_move_vals_custom(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))

        # Create Journal Entry for products leaving the company
        if self._is_out():
            cost = -1 * cost
            if self._is_returned(valued_type='out'):
                am_vals.append(self.with_company(company_from).with_context(is_returned=True)._prepare_account_move_vals_custom(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))
            else:
                am_vals.append(self.with_company(company_from)._prepare_account_move_vals_custom(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost))

        if self.company_id.anglo_saxon_accounting:
            # Creates an account entry from stock_input to stock_output on a dropship move. https://github.com/odoo/odoo/issues/12687
            if self._is_dropshipped():
                if cost > 0:
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals_custom(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))
                else:
                    cost = -1 * cost
                    am_vals.append(self.with_company(self.company_id)._prepare_account_move_vals_custom(acc_valuation, acc_dest, journal_id, qty, description, svl_id, cost))
            elif self._is_dropshipped_returned():
                if cost > 0 and self.location_dest_id._should_be_valued():
                    am_vals.append(self.with_company(self.company_id).with_context(is_returned=True)._prepare_account_move_vals_custom(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))
                elif cost > 0:
                    am_vals.append(self.with_company(self.company_id).with_context(is_returned=True)._prepare_account_move_vals_custom(acc_dest, acc_valuation, journal_id, qty, description, svl_id, cost))
                else:
                    cost = -1 * cost
                    am_vals.append(self.with_company(self.company_id).with_context(is_returned=True)._prepare_account_move_vals_custom(acc_valuation, acc_src, journal_id, qty, description, svl_id, cost))

        return am_vals

    def _prepare_account_move_vals_custom(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        self.ensure_one()
        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        svl = self.env['droga.stock.valuation.layer'].browse(svl_id)
        move_ids = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, svl.svl_id, description)

        #Custom added to back post
        if svl.move_date:
            date = svl.move_date
        elif self.env.context.get('force_period_date'):
            date = self.env.context.get('force_period_date')
        elif svl.account_move_line_id:
            date = svl.account_move_line_id.date
        else:
            date = fields.Date.context_today(self)
        return {
            'journal_id': journal_id,
            'line_ids': move_ids,
            'partner_id': valuation_partner_id,
            'date': date,
            'ref': description,
            'stock_move_id': self.id,
            #'droga_stock_valuation_layer_ids': [(6, None, [svl_id])],
            #'stock_valuation_layer_ids': [(6, None, [svl.svl_id])],
            'move_type': 'entry',
            'is_storno': self.env.context.get('is_returned') and self.env.company.account_storno,
        }

class DrogaAccountMove(models.Model):
    _inherit = 'account.move'

    droga_stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'account_move_id', string='Stock Valuation Layer')
