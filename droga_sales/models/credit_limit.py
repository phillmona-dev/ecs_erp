from datetime import timedelta

from stdnum import cr
from stdnum.ch import uid

from odoo import models, fields, api
from odoo.addons.base.models.ir_model import IrModelData
from odoo.exceptions import ValidationError


class cust_credit_limit(models.Model):
    _inherit='res.partner'
    cust_credit_limit = fields.Float(string='Credit limit',tracking=True)
    unsettled_amount = fields.Float(string='Unsettled amount')
    available_amount = fields.Float(string='Credit balance',compute='_compute_cust_unsetlled_amount')

    def _compute_cust_unsetlled_amount(self):
        for rec in self:
            rec.available_amount = rec.cust_credit_limit-rec.unsettled_amount

class cust_credit_account_move(models.Model):
    _inherit = 'account.move'
    def action_post(self):
        result = super(cust_credit_account_move, self).action_post()
        for inv in self:
            for line in inv['line_ids']:
                if line.account_type=='asset_receivable':
                    line.partner_id.unsettled_amount+=line.amount_currency
        return result

    #This is used for forcing reversal to have a draft state
    def _reverse_moves(self, default_values_list=None, cancel=False):
        return super(cust_credit_account_move, self)._reverse_moves()


class cust_sales_credit_limit(models.Model):
    _inherit = 'sale.order'
    available_amount=fields.Float(string='Credit balance',related='partner_id.available_amount')
    tender_origin_form = fields.Many2one('droga.tender.master', readonly=True)

    @api.model
    def create(self, vals):
        result = super(cust_sales_credit_limit, self).create(vals)
        for so in result:
            if so.partner_id.available_amount <so.amount_total and so.payment_term_id.apply_credit_limit:
                raise ValidationError("You cannot exceed credit limit!")
        return result

    def action_confirm(self):
        order_lines_core = self.order_line.filtered(
            lambda x: not x.wareh)
        if (len(order_lines_core) > 0):
            raise ValidationError("Warehouse must be filled for each order line.")

        result = super(cust_sales_credit_limit, self).action_confirm()

        for so in self:
            if so.partner_id.available_amount <so.amount_total and so.payment_term_id.apply_credit_limit:
                raise ValidationError("You cannot exceed credit limit!")
        return result

    def store_issue_placement_order(self):
        return {
            'name': 'Sample request',
            'view_type': 'tree',
            'view_mode': 'tree,form',
            'res_model': 'droga.inventory.consignment.issue',
            'views': [
                [self.env.ref('droga_inventory.droga_inventory_consignment_issue_view_tree_sales').id, 'tree'],
                [self.env.ref('droga_inventory.droga_inventory_consignment_issue_view_form').id, 'form']],
            'type': 'ir.actions.act_window',
            'context': {
                'default_sales_placement_origin_form': self.id,
                'default_customer': self.partner_id.id,
                'default_issue_type': 'SAP'
            },
            'domain':
                ([('sales_placement_origin_form', '=', self.id)])
        }

class inventory_placement_extension(models.Model):
    _inherit = 'droga.inventory.consignment.issue'
    sales_placement_origin_form=fields.Many2one('sale.order',readonly=True)

class cust_sales_no_create_after_invoice(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super(cust_sales_no_create_after_invoice, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        date_deadline = self.order_id.commitment_date or (self.order_id.date_order + timedelta(days=self.customer_lead or 0.0))
        date_planned = date_deadline - timedelta(days=self.order_id.company_id.security_lead)
        values.update({
            'group_id': group_id,
            'sale_line_id': self.id,
            'date_planned': date_planned,
            'date_deadline': date_deadline,
            'route_ids': self.route_id,
            'warehouse_id': self.wareh or False,
            'partner_id': self.order_id.partner_shipping_id.id,
            'product_description_variants': self.with_context(lang=self.order_id.partner_id.lang)._get_sale_order_line_multiline_description_variants(),
            'company_id': self.order_id.company_id,
            'product_packaging_id': self.product_packaging_id,
            'sequence': self.sequence,
        })
        return values

    #Restrict multiple sales order invoicing
    @api.model
    def create(self, vals):
        if self.order_id.state!='draft' and self.order_id.state:
            raise ValidationError("Sales order is already invoiced!")
        else:
            return super(cust_sales_no_create_after_invoice, self).create(vals)


class payment_term_no_credit(models.Model):
    _inherit = 'account.payment.term'
    apply_credit_limit=fields.Boolean(string='Apply credit limit',default=True)

