# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class EcsPaymentRequest(models.Model):
    """
    Payment Request — multi-level approval workflow for disbursements.

    Uses the ECS approval workflow, company-scoped record rules, budget
    validation, and controlled account.payment generation.
    """
    _name = 'ecs.finance.payment.request'
    _description = 'Payment Request'
    _order = 'name desc, id desc'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'ecs.approval.mixin',
        'ecs.currency.word.mixin',
    ]
    _rec_name = 'name'

    # ── Identity ──────────────────────────────────────────────────────
    name = fields.Char(
        'Reference', default='New', copy=False,
        readonly=True, index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, default=lambda self: self.env.company,
        readonly=True, states={'draft': [('readonly', False)]},
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id', store=True, string='Currency'
    )

    # ── Requester ─────────────────────────────────────────────────────
    request_by = fields.Many2one(
        'hr.employee', 'Requested By',
        domain="[('company_id','=',company_id)]",
        default=lambda self: self._get_employee(),
    )
    department_id = fields.Many2one(
        'hr.department', 'Department',
        domain="[('company_id','=',company_id)]",
    )
    request_date = fields.Date(
        'Request Date', required=True, default=fields.Date.today,
        readonly=True, states={'draft': [('readonly', False)]},
    )

    # ── Payment Details ───────────────────────────────────────────────
    purpose = fields.Text('Purpose / Description', required=True)
    amount  = fields.Monetary(
        'Amount', currency_field='currency_id', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
    )
    payment_type = fields.Selection([
        ('cash',          'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check',         'Check'),
    ], string='Payment Method', required=True, default='bank_transfer')

    payee_id = fields.Many2one(
        'res.partner', 'Payee',
        domain="[('active','=',True)]",
    )
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Payee Bank Account',
        domain="[('partner_id','=',payee_id)]",
    )

    # ── Accounting ────────────────────────────────────────────────────
    expense_account_id = fields.Many2one(
        'account.account', 'Expense Account',
        domain="[('deprecated','=',False)]",
    )
    analytic_distribution = fields.Json(
        'Cost Center / Analytic',
        help='Analytic distribution for this payment.'
    )
    budget_position_id = fields.Many2one(
        'ecs.budget.position', 'Budget Line',
        domain="[('company_id','=',company_id)]",
    )

    # ── Budget Check ─────────────────────────────────────────────────
    remaining_budget = fields.Float(
        'Remaining Budget', compute='_compute_remaining_budget',
        help='Available budget after existing commitments.'
    )
    is_over_budget = fields.Boolean(
        'Over Budget?', compute='_compute_remaining_budget',
    )

    # ── Amount in Words ───────────────────────────────────────────────
    amount_in_words = fields.Char(
        'Amount in Words', compute='_compute_amount_in_words', store=True
    )

    # ── Generated Payment ─────────────────────────────────────────────
    payment_id = fields.Many2one(
        'account.payment', 'Generated Payment',
        readonly=True, copy=False,
    )

    # ── Approval metadata (from ecs.approval.mixin) ───────────────────
    # state, rejection_reason, approval_log_ids, submitted_by, approved_by etc.
    # already defined in mixin — no duplication needed

    # ── Compute ───────────────────────────────────────────────────────

    @api.depends('amount', 'currency_id')
    def _compute_amount_in_words(self):
        for rec in self:
            rec.amount_in_words = rec.amount_to_word(rec.amount or 0.0)

    @api.depends('budget_position_id', 'expense_account_id', 'amount', 'company_id')
    def _compute_remaining_budget(self):
        for rec in self:
            if not rec.budget_position_id or not rec.expense_account_id:
                rec.remaining_budget = 0.0
                rec.is_over_budget = False
                continue
            if 'ecs.finance.commitment' not in self.env:
                rec.remaining_budget = 0.0
                rec.is_over_budget = False
                continue
            remaining = self.env['ecs.finance.commitment'].get_remaining_budget(
                budget_position_id=rec.budget_position_id.id,
                expense_account_id=rec.expense_account_id.id,
                company_id=rec.company_id.id,
            )
            rec.remaining_budget = remaining
            rec.is_over_budget = remaining < (rec.amount or 0.0)

    # ── Sequence ──────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ecs.sequence.service'].get_transaction_no(
                    prefix='PMR',
                    date=vals.get('request_date') or fields.Date.today(),
                    company_id=vals.get('company_id') or self.env.company.id,
                )
        return super().create(vals_list)

    # ── Approval hooks (ecs.approval.mixin overrides) ─────────────────

    def _validate_before_submit(self):
        """Validate required fields before allowing submission."""
        for rec in self:
            if not rec.amount or rec.amount <= 0:
                raise UserError(_('Amount must be greater than zero.'))
            if not rec.purpose:
                raise UserError(_('Purpose / Description is required.'))
            if not rec.payee_id:
                raise UserError(_('Payee is required before submitting.'))

    def _get_submit_approver(self):
        """Route to department manager on submission."""
        self.ensure_one()
        if self.department_id and self.department_id.manager_id:
            return self.department_id.manager_id.user_id
        return False

    def _get_approve_approver(self):
        """
        Route to next approver based on current state and amount tier.
        Budget Controller → Finance Manager → (CEO if > threshold)
        """
        self.ensure_one()
        if self.state == 'submitted':
            # L2: Budget Controller
            group = self.env.ref('ecs_approvals.group_ecs_finance_controller', raise_if_not_found=False)
            if group:
                users = group.users.filtered(
                    lambda u: self.company_id in u.company_ids
                )
                return users[:1] if users else False
        elif self.state == 'verified':
            # L3: Finance Manager
            group = self.env.ref('ecs_approvals.group_ecs_finance_manager', raise_if_not_found=False)
            if group:
                users = group.users.filtered(
                    lambda u: self.company_id in u.company_ids
                )
                return users[:1] if users else False
        return False

    def _on_final_approval(self):
        """Record budget commitment when payment request is fully approved."""
        if 'ecs.finance.commitment' not in self.env:
            return
        for rec in self:
            if rec.budget_position_id and rec.expense_account_id:
                self.env['ecs.finance.commitment'].sudo().create({
                    'document_type':       'payment_request',
                    'payment_request_id':  rec.id,
                    'amount':              rec.amount,
                    'budget_position_id':  rec.budget_position_id.id,
                    'expense_account_id':  rec.expense_account_id.id,
                    'analytic_distribution': rec.analytic_distribution,
                    'company_id':          rec.company_id.id,
                    'state':               'active',
                })

    def action_cancel(self):
        """Close any active budget commitments before cancelling."""
        if 'ecs.finance.commitment' not in self.env:
            return super().action_cancel()
        for rec in self:
            commitments = self.env['ecs.finance.commitment'].search([
                ('payment_request_id', '=', rec.id),
                ('state', '=', 'active'),
            ])
            commitments.write({'state': 'cancelled'})
        return super().action_cancel()

    # ── Generate Payment ──────────────────────────────────────────────

    def action_generate_payment(self):
        """
        Create an account.payment from an approved payment request.
        Only callable when state == 'approved'.
        """
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved payment requests can generate a payment.'))
        if self.payment_id:
            raise UserError(
                _('A payment has already been generated for this request: %s') % self.payment_id.name
            )
        payment_vals = {
            'payment_type':     'outbound',
            'partner_type':     'supplier',
            'partner_id':       self.payee_id.id,
            'amount':           self.amount,
            'currency_id':      self.currency_id.id,
            'date':             fields.Date.today(),
            'ref':              self.name,
            'company_id':       self.company_id.id,
            'memo':             self.purpose,
        }

        payment = self.env['account.payment'].sudo().with_company(
            self.company_id
        ).create(payment_vals)

        self.payment_id = payment
        self.message_post(
            body=_('Payment %s generated from this request.') % payment.name,
            subtype_xmlid='mail.mt_note',
        )
        return self.action_view_payment()

    def action_view_payment(self):
        """Open the linked payment in a form view."""
        self.ensure_one()
        if not self.payment_id:
            return {}
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Helpers ───────────────────────────────────────────────────────

    def _get_employee(self):
        """Return the employee record for the current user in this company."""
        return self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
