from odoo import models, fields, api


class sales_report_fields(models.Model):
    _inherit = 'sale.order'
    cust_location=fields.Many2one('droga.crm.settings.city',related='partner_id.city_name',store=True)

class sales_report_det_fields(models.Model):
    _inherit='sale.order.line'
    cust_location=fields.Many2one('droga.crm.settings.city',related='order_id.cust_location',store=True)

    date_order_det = fields.Datetime('droga.crm.settings.city', related='order_id.date_order',store=True)
    order_type_det = fields.Selection([
        ('IM', 'Import'),
        ('WS', 'Wholesale'), ('PT', 'Physiotherapy')], string='Order from',related='order_id.order_type',store=True)
    payment_term_det = fields.Many2one('account.payment.term',
        string="Payment Terms",related='order_id.payment_term_id',store=True)
    cash_or_credit=fields.Char(compute='_cash_or_credit')

    def _cash_or_credit(self):
        for rec in self:
            if rec.payment_term_det.apply_credit_limit:
                rec.cash_or_credit='Credit'
            else:
                rec.cash_or_credit = 'Cash'

    crm_group1 = fields.Many2one('droga.crm.settings.prod_group', related='product_id.crm_group', store=True)
    is_core=fields.Boolean(related='product_id.is_core_product',store=True)

    itemcode=fields.Char(related='product_id.default_code')
    itemdesc = fields.Char(related='product_id.name')
    itemcateg=fields.Many2one('product.category',related='product_id.categ_id')

    invoiced_amt=fields.Float('Invoiced Amount',compute='_get_invoiced_amount',store=True)
    def _get_invoiced_amount(self):
        for rec in self:
            rec.invoiced_amt=rec.qty_invoiced*rec.price_unit

    sales_initiator_det=fields.Char(related='order_id.sales_initiator')
    sales_dept=fields.Char(compute='_get_sales_dep')
    def _get_sales_dep(self):
        for rec in self:
            if not rec.sales_initiator_det:
                rec.sales_dept = ' '
            elif rec.sales_initiator_det.startswith('SR'):
                rec.sales_dept='Marketing'
            elif rec.sales_initiator_det.startswith('Ten') or rec.sales_initiator_det.startswith('TEN'):
                rec.sales_dept = 'Tender'
            else:
                rec.sales_dept = 'Employee'
    invoice_date=fields.Date('Invoice date',compute='_get_invoice_date')

    def _get_invoice_date(self):
        for rec in self:
            if len(rec.invoice_lines)>0:
                rec.invoice_date=rec.invoice_lines[0].move_id.invoice_date
            else:
                rec.invoice_date=False