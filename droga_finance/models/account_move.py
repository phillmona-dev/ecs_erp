from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountMove(models.Model):
    _inherit = "account.move"

    purpose = fields.Char("Purpose")
    vendor_customer_name = fields.Char("Customer/Vendor Name")
    withholding_no = fields.Char("Withholding Ref")

    @api.depends("amount_total")
    def _compute_amount_word(self):
        for record in self:
            record.untaxed_amount_word = str(
                record.currency_id.amount_to_text(record.amount_untaxed))
            record.amount_total_word = str(
                record.currency_id.amount_to_text(record.amount_total))
            if record.withholding_two_percent != 0:
                record.tax_amount_word = str(
                    record.currency_id.amount_to_text(record.withholding_two_percent))
            elif record.withholding_thirty_percent != 0:
                record.tax_amount_word = str(
                    record.currency_id.amount_to_text(record.withholding_thirty_percent))

    @api.depends("amount_total")
    def _comput_witholding_amount(self):
        tax_amount1 = 0
        tax_amount2 = 0
        for record in self.line_ids:
            if record.name == 'Purchase withholding 2%':
                tax_amount1 += abs(record.balance)
            elif record.name == 'Purchase withholding 30%':
                tax_amount2 += abs(record.balance)

        self.withholding_two_percent = tax_amount1
        self.withholding_thirty_percent = tax_amount2

    transaction_type = fields.Many2one("account.transaction.type")
    transaction_no = fields.Char("Transaction Number", default='New')
    untaxed_amount_word = fields.Char(
        compute='_compute_amount_word', store=True)
    amount_total_word = fields.Char(
        compute='_compute_amount_word', store=True)
    tax_amount_word = fields.Char(
        compute='_compute_amount_word', store=True)

    withholding_two_percent = fields.Float(
        compute='_comput_witholding_amount', store=True)
    withholding_thirty_percent = fields.Float(
        compute='_comput_witholding_amount', store=True)

    @api.model
    def create(self, vals):
        # generate transaction number
        res = super(AccountMove, self).create(vals)
        return res

    def write(self, vals):
        return super(AccountMove, self).write(vals)
