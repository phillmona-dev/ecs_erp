from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    transaction_type = fields.Many2one("account.transaction.type")
    payment_request_id = fields.Many2one("droga.account.payment.request")
    purpose = fields.Char("Purpose")

    check_due_date = fields.Date("Check Due Date")
    vendor_supplier = fields.Char("Vendor/Customer Name")

    is_check_printed = fields.Selection([('Yes', 'Yes'), ('No', 'No')], default='No')

    @api.model
    def create(self, vals):
        res = super(AccountPayment, self).create(vals)
        # enable when manual transaction number stops
        self.generate_transaction_type(res)
        return res

    @api.onchange('transaction_type', 'journal_id', 'payment_type')
    def _load_transaction_type(self):
        res = {}
        for record in self:
            if record.payment_type == "outbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "outbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Cash')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Cash')]}

        return res

    # generate transaction number for check payment voucher,petty cash and bank deposit
    def generate_transaction_type(self, res):
        transaction_type_no = None
        # search record from account.move
        for record in res:
            # Payment using cash
            if record.payment_type == 'outbound' and record.journal_id.type == "cash":
                transaction_type_no = self.get_transaction_no("Payment", "Cash", res)
            elif record.payment_type == 'outbound' and record.journal_id.type == "bank":
                transaction_type_no = self.get_transaction_no("Payment", "Bank", res)  # Check payment voucher
            elif record.payment_type == 'inbound' and record.journal_id.type == "cash":
                transaction_type_no = self.get_transaction_no("Receipt", "Cash", res)
            elif record.payment_type == 'inbound' and record.journal_id.type == "bank":
                transaction_type_no = self.get_transaction_no("Receipt", "Bank", res)

                # update account move
            record.move_id.write({'transaction_type': transaction_type_no['transaction_type'],
                                  'transaction_no': transaction_type_no['transaction_no']})

    def get_transaction_no(self, transaction_type, payment_method, res):
        transaction = {'transaction_type': '-', 'transaction_no': 'New'}
        now = datetime.today().date()
        fiscal_year = self.env['account.fiscal.year'].search(
            [('date_from', '<=', now), ('date_to', '>=', now), ('company_id', '=', res.company_id.id)])

        sequence = None
        if fiscal_year:
            # get transaction type
            transaction_types = self.env["account.transaction.type"].search(
                [('payment_method', '=', payment_method), ('transaction_type', '=', transaction_type),
                 ('company_id', '=', res.company_id.id)])
            for record in transaction_types.posting_cycles:
                if record.fiscal_year.id == fiscal_year.id:
                    # get sequence
                    sequence = record.sequence

            if sequence:
                # generate new sequence
                # get sequence number for each company
                # transaction_no = self.env['ir.sequence'].next_by_code(sequence.code) or '/'
                transaction_no = sequence.next_by_id()
                # update transaction
                transaction.update({'transaction_type': transaction_types.id, 'transaction_no': transaction_no})
                return transaction
            else:
                raise ValidationError(
                    "Sequence is not defined for the transaction type")

    def print_check(self):
        res1 = self.env.ref('droga_finance.droga_account_check_printout_cbe_action').report_action(self)
        return res1


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    transaction_type = fields.Many2one("account.transaction.type")

    @api.onchange('transaction_type', 'journal_id', 'payment_type')
    def _load_transaction_type(self):
        res = {}
        for record in self:
            if record.payment_type == "outbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "outbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Cash')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Cash')]}

        return res
