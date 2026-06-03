# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    """
    Account Payment extensions for ECS ERP.

    Provides company-scoped payment transaction types, generated transaction
    references, amount-in-words, check printing fields, and payment request
    linkage.
    """
    _inherit = 'account.payment'

    # ── Transaction Reference ─────────────────────────────────────────
    transaction_no = fields.Char(
        'Transaction No', copy=False, readonly=True, index=True,
    )
    transaction_type_id = fields.Many2one(
        'ecs.finance.transaction.type',
        string='Transaction Type',
        domain="[('company_id','=',company_id)]",
        tracking=True,
    )

    # ── Amount in Words ───────────────────────────────────────────────
    amount_in_words = fields.Char(
        'Amount in Words',
        compute='_compute_amount_in_words',
        store=True,
    )

    # ── Check Printing ────────────────────────────────────────────────
    check_number   = fields.Char('Check No', copy=False)
    check_date     = fields.Date('Check Date')
    payee_name     = fields.Char(
        'Payee Name',
        compute='_compute_payee_name', store=True, readonly=False,
        help='Name to print on check. Defaults to partner name.'
    )

    # ── Payment Request linkage ───────────────────────────────────────
    payment_request_id = fields.Many2one(
        'ecs.finance.payment.request',
        string='Payment Request', readonly=True, copy=False,
    )

    # ── Compute ───────────────────────────────────────────────────────

    @api.depends('amount', 'currency_id')
    def _compute_amount_in_words(self):
        mixin = self.env['ecs.currency.word.mixin']
        for rec in self:
            try:
                rec.amount_in_words = mixin.amount_to_word(rec.amount or 0.0)
            except Exception:
                rec.amount_in_words = ''

    @api.depends('partner_id')
    def _compute_payee_name(self):
        for rec in self:
            rec.payee_name = rec.partner_id.name if rec.partner_id else ''

    # ── Sequence ──────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('transaction_type_id') and not vals.get('transaction_no'):
                trans_type = self.env['ecs.finance.transaction.type'].browse(
                    vals['transaction_type_id']
                )
                vals['transaction_no'] = trans_type.get_next_reference(
                    date=vals.get('date')
                )
        return super().create(vals_list)
