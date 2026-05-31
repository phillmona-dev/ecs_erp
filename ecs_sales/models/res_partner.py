# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResPartner(models.Model):
    """
    Customer extensions for Credit Limit tracking.
    Fields are made company-dependent so that credit limit can vary per company.
    """
    _inherit = 'res.partner'

    cust_credit_limit = fields.Float(
        string='Credit Limit',
        company_dependent=True,
        tracking=True,
        help="Credit limit allowed for credit terms in the current company."
    )
    unsettled_amount = fields.Monetary(
        compute='_compute_credit_balances',
        string='Unsettled Amount',
        help="Total unpaid or partially paid posted customer invoices for the current company."
    )
    available_amount = fields.Float(
        compute='_compute_credit_balances',
        string='Available Credit Balance',
        help="Remaining credit limit available for new orders (Credit Limit - Unsettled Amount)."
    )

    @api.depends_context('company')
    def _compute_credit_balances(self):
        """Compute unsettled invoices and available credit limit for the current company context."""
        company = self.env.company
        account_move = self.env['account.move']

        for partner in self:
            # Search for unpaid or partially paid posted sale invoices for this partner in the current company
            unpaid_moves = account_move.search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('company_id', '=', company.id),
            ])

            # Calculate total residual (remaining unpaid amount) in company currency
            total_unsettled = sum(unpaid_moves.mapped('amount_residual_signed'))
            partner.unsettled_amount = total_unsettled

            # Available credit
            limit = partner.cust_credit_limit or 0.0
            partner.available_amount = limit - total_unsettled
