from datetime import datetime
from datetime import timedelta

from stdnum import cr
from stdnum.ch import uid

from odoo import models, fields, api
from odoo.addons.base.models.ir_model import IrModelData
from odoo.exceptions import ValidationError


class cust_credit_limit(models.Model):
    _inherit = 'res.partner'
    cust_credit_limit = fields.Float(string='Credit limit', tracking=True)
    unsettled_amount = fields.Monetary(compute='_compute_balance', string='Unsettled amount')
    available_amount = fields.Float(string='Credit balance', compute='_compute_balance')
    vat = fields.Char(string='Tin No', index=True,
                      help="The Tax Identification Number. Complete it if the contact is subjected to government taxes. Used in some legal statements.")

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for record in self:
            record.unsettled_amount = record.credit - record.debit
            record.available_amount = record.cust_credit_limit - record.unsettled_amount


class cust_sales_credit_limit(models.Model):
    _inherit = 'sale.order'
    available_amount = fields.Float(string='Credit balance', related='partner_id.available_amount')
    tender_origin_form = fields.Many2one('droga.tender.master', readonly=True)
    cash_upfront = fields.Float(string='Down payment')
    pay_type = fields.Boolean(related='payment_term_id.apply_credit_limit')
    mature_amount = fields.Monetary('Matured amount', compute='_get_mature_amount')
    show_invoice_button = fields.Boolean(compute='_get_mature_amount')
    manual_price = fields.Boolean('Manual price', default=False, required=True, tracking=True)
    Vat_no = fields.Char(related='partner_id.vat',readonly='True')
    cust_id = fields.Integer(related='partner_id.id',readonly='True')
    sales_type = fields.Char('Sales order type', compute='_get_so_type', store=True)
    supporters=fields.Many2many('droga.pro.sales.master',string='Supporters')

    order_type = fields.Selection([
        ('IM', 'Import'),
        ('WS', 'Wholesale'), ('PT', 'Physiotherapy')], string='Order from', required=True)

    @api.depends('payment_term_id')
    def _get_so_type(self):
        for rec in self:
            if rec.payment_term_id.apply_credit_limit:
                rec.sales_type = 'Credit sales'
            elif rec.payment_term_id.name == 'Sales return':
                rec.sales_type = 'Sales return'
            else:
                rec.sales_type = 'Cash sales'

    @api.depends('partner_id')
    def _get_mature_amount(self):
        for rec in self:
            if rec.partner_id.vat != '0000000000':
                matured_invoices = self.env['account.move'].search(
                    [('state', '=', 'posted'), ('journal_id.type', '=', 'sale'),
                     ('invoice_date_due', '<=', datetime.now()),
                     ('payment_state', 'in', ['not_paid', 'partial']), ('partner_id.vat', '=', rec.partner_id.vat), '|',
                     ('partner_id.active', '=', True), ('partner_id.active', '=', False)])
            else:
                matured_invoices = self.env['account.move'].search(
                    [('state', '=', 'posted'), ('journal_id.type', '=', 'sale'),
                     ('invoice_date_due', '<=', datetime.now()),
                     ('payment_state', 'in', ['not_paid', 'partial']), ('partner_id', '=', rec.partner_id.id), '|',
                     ('partner_id.active', '=', True), ('partner_id.active', '=', False)])

            tot_amount = 0
            for mi in matured_invoices:
                tot_amount = tot_amount + (
                    mi['amount_total_signed'] if mi['amount_residual'] == 0 else mi['amount_residual'])
            rec.mature_amount = tot_amount
            rec.show_invoice_button = False if rec.mature_amount == 0 else True

    def action_cancel(self):
        for rec in self:
            if rec.invoice_status not in ('no','to invoice'):
                raise ValidationError("The sales order is already invoiced, hence can not be cancelled.")

            if len(rec.order_line.filtered(lambda x: x.qty_delivered >0)) > 0:
                raise ValidationError("There are dispatched items under the sales order, hence can not be cancelled.")
            pass
        return super(cust_sales_credit_limit, self).action_cancel()

    @api.model
    def create(self, vals):

        result = super(cust_sales_credit_limit, self).create(vals)
        for so in result:
            if not so.partner_id.vat:
                raise ValidationError("Tin No must be registered for customer!")
            if not so.pr_sales and self.env.user.name.startswith('CRM'):
                raise ValidationError("Please login before registering a sales order!")
            if so.partner_id.available_amount + so.cash_upfront < so.amount_total and so.payment_term_id.apply_credit_limit:
                raise ValidationError("You cannot exceed credit limit!")
        return result


class inventory_placement_extension(models.Model):
    _inherit = 'droga.inventory.consignment.issue'
    sales_placement_origin_form = fields.Many2one('sale.order', readonly=True)


class cust_sales_no_create_after_invoice(models.Model):
    _inherit = 'sale.order.line'
    manual_price = fields.Boolean(related='order_id.manual_price')
    expiry_date_html = fields.Html('Expiration date', compute='_get_expiry', default='')
    batch_html = fields.Html('Batch No', compute='_get_expiry', default='')

    order_type = fields.Selection([
        ('IM', 'Import'),
        ('WS', 'Wholesale'), ('PT', 'Physiotherapy')], string='Order from', related='order_id.order_type')

    def _get_expiry(self):
        for rec in self:
            rec.expiry_date_html = ''
            rec.batch_html
            try:
                for move in rec.move_ids:
                    count = len(move.move_line_ids) - 1
                    for id, move_line in enumerate(move.move_line_ids):
                        rec.expiry_date_html = (
                                                   rec.expiry_date_html if rec.expiry_date_html else '') + move_line.lot_id.expiration_date.strftime(
                            "%B %d,%Y") + ('\n' if id < count else '')
                        rec.batch_html = (
                                             rec.batch_html if rec.batch_html else '') + move_line.lot_id.name + ' (' + str(
                            move_line.qty_done) + ')' + ('\n' if id < count else '')
            except:
                rec.expiry_date_html = ''
                rec.batch_html = ''

    def _prepare_procurement_values(self, group_id=False):

        values = super(cust_sales_no_create_after_invoice, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        date_deadline = self.order_id.commitment_date or (
                self.order_id.date_order + timedelta(days=self.customer_lead or 0.0))
        date_planned = date_deadline - timedelta(days=self.order_id.company_id.security_lead)
        values.update({
            'group_id': group_id,
            'sale_line_id': self.id,
            'date_planned': date_planned,
            'date_deadline': date_deadline,
            'route_ids': self.route_id,
            'warehouse_id': self.wareh or False,
            'partner_id': self.order_id.partner_shipping_id.id,
            'product_description_variants': self.with_context(
                lang=self.order_id.partner_id.lang)._get_sale_order_line_multiline_description_variants(),
            'company_id': self.order_id.company_id,
            'product_packaging_id': self.product_packaging_id,
            'sequence': self.sequence,
        })
        return values

    # Restrict multiple sales order invoicing
    @api.model
    def create(self, vals):
        if self.order_id.state != 'draft' and self.order_id.state:
            raise ValidationError("Sales order is already invoiced!")
        else:
            return super(cust_sales_no_create_after_invoice, self).create(vals)


class payment_term_no_credit(models.Model):
    _inherit = 'account.payment.term'
    apply_credit_limit = fields.Boolean(string='Apply credit limit', default=True, Tracking=True)
    deliv_after_payment = fields.Boolean(string='Delivery after payment', default=False)


class payment_term_no_credit_messages(models.Model):
    _name = 'account.payment.term'
    _inherit = ['account.payment.term', 'mail.thread', 'mail.activity.mixin', 'image.mixin']
