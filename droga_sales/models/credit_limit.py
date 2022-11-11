from odoo import models, fields, api
from odoo.exceptions import ValidationError


class cust_credit_limit(models.Model):
    _inherit='res.partner'
    cust_credit_limit = fields.Float(string='Credit limit')
    unsettled_amount = fields.Float(string='Unsettled amount')
    available_amount = fields.Float(string='Available credit',compute='_compute_cust_unsetlled_amount')

    def _compute_cust_unsetlled_amount(self):
        for rec in self:
            rec.available_amount = rec.cust_credit_limit-rec.unsettled_amount

class cust_credit_account_move(models.Model):
    _inherit = 'account.move'
    def action_post(self):
        result = super(cust_credit_account_move, self).action_post()
        for inv in self:
            for line in inv['line_ids']:
                if line.account_type=='asset_receivable' or line.account_type=='liability_payable':
                    line.partner_id.unsettled_amount+=line.amount_currency
        return result

    #This is used for forcing reversal to have a draft state
    def _reverse_moves(self, default_values_list=None, cancel=False):
        return super(cust_credit_account_move, self)._reverse_moves()


class cust_sales_credit_limit(models.Model):
    _inherit = 'sale.order'
    def action_confirm(self):
        result = super(cust_sales_credit_limit, self).action_confirm()
        for so in self:
            if so.partner_id.available_amount <so.amount_total:
                raise ValidationError("You cannot exceed credit limit!")
        return result


class cust_sales_no_create_after_invoice(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def create(self, vals):
        if self.order_id.state!='draft' and self.order_id.state:
            raise ValidationError("Sales order is already invoiced!")
        else:
            return super(cust_sales_no_create_after_invoice, self).create(vals)
