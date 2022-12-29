from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountMove(models.Model):

    _inherit = "account.move"

    purpose = fields.Char("Purpose")



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
        """
        if 'transaction_type' in vals:
            if vals['transaction_type'] != '':
                # get sequence code for the current fisacl year
                # get current discal year
                now = datetime.today().date()
                fisacl_year = self.env['account.fiscal.year'].search(
                    [('date_from', '<=', now), ('date_to', '>=', now)])

                sequence = None
                if fisacl_year:
                    #get transaction type
                    transaction_type=self.env["account.transaction.type"].search([('id','=',vals['transaction_type'])])
                    for record in transaction_type.posting_cycles:
                        if record.fiscal_year.id == fisacl_year.id:
                            # get sequence
                            sequence = record.sequence

                    if sequence:
                        # generate new sequence
                        # get sequence number for each company
                        vals['transaction_no'] = self.env['ir.sequence'].next_by_code(
                            sequence.code) or '/'
                    else:
                        raise ValidationError("Sequence is not defined for the transaction type")
        else:
            raise ValidationError("Transaction type is not selected")
        """
        return super(AccountMove, self).create(vals)

    def write(self, vals):
        if 'transaction_type' in vals:
            if vals['transaction_type'] != '':
                # get sequence code for the current fisacl year
                # get current discal year
                now = datetime.today().date()
                fisacl_year = self.env['account.fiscal.year'].search(
                    [('date_from', '<=', now), ('date_to', '>=', now)])

                sequence = None
                if fisacl_year:
                    # get transaction type
                    transaction_type = self.env["account.transaction.type"].search(
                        [('id', '=', vals['transaction_type'])])
                    for record in transaction_type.posting_cycles:
                        if record.fiscal_year.id == fisacl_year.id:
                            # get sequence
                            sequence = record.sequence

                    if sequence:
                        # generate new sequence
                        # get sequence number for each company
                        vals['transaction_no'] = self.env['ir.sequence'].next_by_code(
                            sequence.code) or '/'
                    else:
                        raise ValidationError(
                            "Sequence is not defined for the transaction type")
        # else:
            #raise ValidationError("Transaction type is not selected")
        return super(AccountMove, self).write(vals)
