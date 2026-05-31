# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Account Move (Invoice/Bill/JV) extensions for ECS ERP.

    Provides amount-in-words, company-scoped transaction types, generated
    references, and configurable withholding entries for ECS finance.
    """
    _inherit = 'account.move'

    # ── Transaction Identity ──────────────────────────────────────────
    transaction_no = fields.Char(
        'Transaction No', copy=False, readonly=True, index=True,
        help='Auto-generated reference number (e.g. CPV/2016/00023).'
    )
    transaction_type_id = fields.Many2one(
        'ecs.finance.transaction.type',
        string='Transaction Type',
        domain="[('company_id','=',company_id)]",
        tracking=True,
        states={'posted': [('readonly', True)], 'cancel': [('readonly', True)]},
    )

    # ── CRV (Cash Receipt Voucher) ────────────────────────────────────
    crv_number = fields.Char('CRV No', copy=False)
    crv_date   = fields.Date('CRV Date')

    # ── Amount in Words ───────────────────────────────────────────────
    amount_in_words = fields.Char(
        'Amount in Words',
        compute='_compute_amount_in_words',
        store=True,
    )

    # ── Withholding ───────────────────────────────────────────────────
    withholding_state = fields.Selection([
        ('not_applicable', 'Not Applicable'),
        ('pending',        'Pending'),
        ('done',           'Withholding Applied'),
    ], string='Withholding Status', default='not_applicable',
       tracking=True, copy=False,
    )
    withholding_amount = fields.Monetary(
        'Withholding Amount', currency_field='currency_id',
        copy=False,
    )
    withholding_entry_id = fields.Many2one(
        'account.move', 'Withholding JV',
        readonly=True, copy=False,
        help='The journal entry created for the withholding deduction.'
    )
    withholding_config_id = fields.Many2one(
        'ecs.finance.withholding.config',
        string='Withholding Rule',
        domain="[('company_id','=',company_id)]",
        readonly=True, copy=False,
    )

    # ── Payment Request Linkage ───────────────────────────────────────
    payment_request_id = fields.Many2one(
        'ecs.finance.payment.request',
        string='Payment Request',
        readonly=True, copy=False,
    )

    # ── Compute ───────────────────────────────────────────────────────

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_in_words(self):
        mixin = self.env['ecs.currency.word.mixin']
        for move in self:
            try:
                move.amount_in_words = mixin.amount_to_word(move.amount_total or 0.0)
            except Exception:
                move.amount_in_words = ''

    # ── Sequence Auto-Generation ──────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('transaction_type_id') and not vals.get('transaction_no'):
                trans_type = self.env['ecs.finance.transaction.type'].browse(
                    vals['transaction_type_id']
                )
                vals['transaction_no'] = trans_type.get_next_reference(
                    date=vals.get('invoice_date') or vals.get('date')
                )
        return super().create(vals_list)

    def write(self, vals):
        if 'transaction_type_id' in vals and not self.transaction_no:
            trans_type = self.env['ecs.finance.transaction.type'].browse(
                vals['transaction_type_id']
            )
            vals['transaction_no'] = trans_type.get_next_reference(date=self.date)
        return super().write(vals)

    # ── Withholding Actions ───────────────────────────────────────────

    def action_compute_withholding(self):
        """
        Compute and set the withholding amount based on the company's
        withholding configuration for this move's vendor/partner.
        Does NOT post an entry yet — just sets the amount for review.
        """
        for move in self:
            if move.state != 'posted':
                raise UserError(_('Can only apply withholding to posted entries.'))
            if move.withholding_state == 'done':
                raise UserError(
                    _('Withholding has already been applied to %s.') % move.name
                )
            config = self.env['ecs.finance.withholding.config'].get_config_for_partner(
                partner=move.partner_id,
                company_id=move.company_id.id,
            )
            if not config:
                raise UserError(
                    _('No withholding configuration found for partner type in company %s. '
                      'Please configure it under Finance → Configuration → Withholding.')
                    % move.company_id.name
                )
            move.withholding_amount  = config.compute_withholding_amount(move.amount_untaxed)
            move.withholding_config_id = config
            move.withholding_state   = 'pending'

    def action_post_withholding_entry(self):
        """
        Create the withholding journal entry (debit vendor, credit WHT payable).
        Called after reviewing the computed withholding amount.
        """
        for move in self:
            if move.withholding_state != 'pending':
                raise UserError(
                    _('Withholding amount must be computed first. '
                      'Use "Compute Withholding" before posting the entry.')
                )
            config = move.withholding_config_id
            if not config:
                raise UserError(_('No withholding configuration linked. Recompute withholding.'))

            wht_move = self.env['account.move'].sudo().with_company(move.company_id).create({
                'move_type':   'entry',
                'date':        fields.Date.today(),
                'ref':         _('WHT on %s') % move.name,
                'company_id':  move.company_id.id,
                'journal_id':  config.journal_id.id,
                'line_ids': [
                    # Debit: reduce amount due to vendor
                    (0, 0, {
                        'account_id':  move.partner_id.property_account_payable_id.id,
                        'partner_id':  move.partner_id.id,
                        'name':        _('Withholding on %s') % move.name,
                        'debit':       move.withholding_amount,
                        'credit':      0.0,
                        'company_id':  move.company_id.id,
                    }),
                    # Credit: withholding payable account (configured per company)
                    (0, 0, {
                        'account_id':  config.account_id.id,
                        'partner_id':  move.partner_id.id,
                        'name':        _('Withholding Tax Payable — %s') % move.name,
                        'debit':       0.0,
                        'credit':      move.withholding_amount,
                        'company_id':  move.company_id.id,
                    }),
                ],
            })
            wht_move.action_post()
            move.write({
                'withholding_entry_id': wht_move.id,
                'withholding_state':    'done',
            })
            move.message_post(
                body=_(
                    'Withholding entry %s posted — Amount: %s %s'
                ) % (wht_move.name, move.withholding_amount, move.currency_id.symbol),
                subtype_xmlid='mail.mt_note',
            )
