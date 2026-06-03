# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EcsFinanceCommitment(models.Model):
    _name = 'ecs.finance.commitment'
    _description = 'ECS Finance Commitment'
    _order = 'company_id, commitment_date desc, id desc'

    name = fields.Char(default='New', copy=False)
    document_type = fields.Selection(
        [
            ('payment_request', 'Payment Request'),
            ('purchase_request', 'Purchase Request'),
            ('contract', 'Contract'),
            ('other', 'Other'),
        ],
        required=True,
        default='other',
    )
    payment_request_id = fields.Many2one(
        'ecs.finance.payment.request',
        string='Payment Request',
        ondelete='cascade',
    )
    amount = fields.Monetary(required=True)
    committed_amount = fields.Monetary(compute='_compute_committed_amount', store=True)
    budget_position_id = fields.Many2one('ecs.budget.position', string='Budget Line')
    expense_account_id = fields.Many2one('account.account', string='Expense Account')
    analytic_distribution = fields.Json(string='Analytic Distribution')
    commitment_date = fields.Date(default=fields.Date.context_today, required=True)
    state = fields.Selection(
        [
            ('active', 'Active'),
            ('released', 'Released'),
            ('cancelled', 'Cancelled'),
        ],
        default='active',
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('amount', 'state')
    def _compute_committed_amount(self):
        for commitment in self:
            commitment.committed_amount = commitment.amount if commitment.state == 'active' else 0.0

    @api.model
    def get_remaining_budget(self, budget_position_id, expense_account_id, company_id):
        commitments = self.search([
            ('budget_position_id', '=', budget_position_id),
            ('expense_account_id', '=', expense_account_id),
            ('company_id', '=', company_id),
            ('state', '=', 'active'),
        ])
        return -sum(commitments.mapped('committed_amount'))
