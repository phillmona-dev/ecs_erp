from odoo import _, api, fields, models


class AccountPayment(models.Model):

    _inherit = 'account.payment'

    transaction_type = fields.Many2one("account.transaction.type")
    payment_request_id = fields.Many2one("droga.account.payment.request")
    purpose = fields.Char("Purpose")

    @api.model
    def create(self, vals):
        return super(AccountPayment, self).create(vals)

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
                    ('transaction_type', '=', 'Reciept'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Reciept'), ('payment_method', '=', 'Cash')]}

        return res


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
                    ('transaction_type', '=', 'Reciept'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Reciept'), ('payment_method', '=', 'Cash')]}

        return res
