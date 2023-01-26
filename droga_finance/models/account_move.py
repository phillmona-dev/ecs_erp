from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.custom_addons.droga.droga_utility.utility import convert_to_word


class AccountMove(models.Model):
    _inherit = "account.move"

    purpose = fields.Char("Purpose")
    vendor_customer_name = fields.Char("Customer/Vendor Name")
    withholding_no = fields.Char("Withholding Ref")
    sales_initiator = fields.Char("Sales Person", compute="_get_sales_person")

    transaction_type = fields.Many2one("account.transaction.type")
    transaction_no = fields.Char("Transaction Number", default='New')
    untaxed_amount_word = fields.Char(
        compute='_compute_amount_word')
    amount_total_word = fields.Char(
        compute='_compute_amount_word')
    tax_amount_word = fields.Char(
        compute='_compute_amount_word')

    withholding_two_percent = fields.Float(
        compute='_compute_withholding_amount')
    withholding_thirty_percent = fields.Float(
        compute='_compute_withholding_amount')

    @api.model
    def create(self, vals):
        # generate transaction number
        res = super(AccountMove, self).create(vals)
        return res

    def write(self, vals):
        return super(AccountMove, self).write(vals)

    def _compute_amount_word(self):
        for record in self:
            record.untaxed_amount_word = str(
                convert_to_word(record.amount_untaxed))
            record.amount_total_word = str(
                convert_to_word(record.amount_total))
            if record.withholding_two_percent != 0:
                record.tax_amount_word = str(
                    convert_to_word(record.withholding_two_percent))
            elif record.withholding_thirty_percent != 0:
                record.tax_amount_word = str(
                    convert_to_word(record.withholding_thirty_percent))

    def _compute_withholding_amount(self):
        tax_amount1 = 0
        tax_amount2 = 0
        for record in self.invoice_line_ids:
            for tax_id in record.tax_ids:
                if tax_id.name == 'Purchase Withholding 2%':
                    tax_amount1 += abs(record.balance * tax_id.amount / 100)
                elif tax_id.name == 'Purchase Withholding 30%':
                    tax_amount2 += abs(record.balance * tax_id.amount / 100)

        self.withholding_two_percent = tax_amount1
        self.withholding_thirty_percent = tax_amount2

    # get sales person
    def _get_sales_person(self):
        self.sales_initiator = ''
        for record in self:
            # search sales order
            sale_order = self.env["sale.order"].sudo().search([('name', '=', record.invoice_origin)])
            for order in sale_order:
                self.sales_initiator = order.sales_initiator
