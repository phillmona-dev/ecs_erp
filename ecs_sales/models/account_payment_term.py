# -*- coding: utf-8 -*-
from odoo import models, fields

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    apply_credit_limit = fields.Boolean(
        string='Apply Credit Limit',
        default=True,
        help="If checked, sales orders using this payment term will be validated against the customer's credit limit."
    )
