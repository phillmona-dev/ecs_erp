from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountMove(models.Model):

    _inherit = "account.move"

    transaction_type = fields.Many2one("account.transaction.type")
    transaction_no = fields.Char("Transaction Number", default='New')

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
