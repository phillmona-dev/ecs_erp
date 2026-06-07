# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class EcsApprovalMixin(models.AbstractModel):
    """
    Unified approval workflow mixin for all ECS documents.

    Provides one configurable approval workflow for ECS documents across
    finance, procurement, HR, inventory, projects, and treasury.

    Features:
    - Configurable state machine (draft → submitted → approved/cancelled)
    - Full audit log via ecs.approval.log
    - mail.activity routing to next approver
    - Rejection with mandatory reason
    - Works with any model that inherits it

    Usage:
        class MyDocument(models.Model):
            _name = 'my.document'
            _inherit = ['mail.thread', 'mail.activity.mixin', 'ecs.approval.mixin']

            # Define your approval-specific logic by overriding:
            #   _get_submit_approver(self)  → returns res.users
            #   _get_approve_approver(self) → returns res.users
            #   _validate_before_submit(self) → raise UserError if invalid
            #   _on_final_approval(self) → called when last approval done
    """
    _name = 'ecs.approval.mixin'
    _description = 'ECS Approval Workflow Mixin'

    state = fields.Selection([
        ('draft',          'Draft'),
        ('submitted',      'Submitted'),
        ('verified',       'Verified'),
        ('budget_approved','Budget Approved'),
        ('approved',       'Approved'),
        ('cancelled',      'Cancelled'),
    ], string='Status', default='draft', required=True,
       tracking=True, copy=False, index=True)

    rejection_reason = fields.Char('Rejection Reason', copy=False)
    approval_log_ids = fields.Many2many(
        'ecs.approval.log',
        compute='_compute_approval_log_ids',
        string='Approval History', readonly=True
    )
    submitted_by = fields.Many2one('res.users', 'Submitted By',
                                   readonly=True, copy=False)
    submitted_date = fields.Datetime('Submitted On', readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', 'Finally Approved By',
                                  readonly=True, copy=False)
    approved_date = fields.Datetime('Approved On', readonly=True, copy=False)

    def _compute_approval_log_ids(self):
        logs_by_record = self._get_approval_logs_by_record()
        for record in self:
            record.approval_log_ids = logs_by_record.get(record.id, self.env['ecs.approval.log'])

    # ── Public API ────────────────────────────────────────────────────

    def action_submit(self):
        """Submit document for approval."""
        for rec in self:
            rec._validate_before_submit()
            rec._log_approval_action('submit', level=0)
            rec.write({
                'state': 'submitted',
                'submitted_by': self.env.uid,
                'submitted_date': fields.Datetime.now(),
                'rejection_reason': False,
            })
            approver = rec._get_submit_approver()
            if approver:
                rec._create_approval_activity(
                    approver,
                    summary=_('Approval Required: %s') % rec.display_name,
                    note=_('Please review and approve this document.'),
                )
            rec.message_post(
                body=_('Document submitted for approval by %s.') % self.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_approve(self):
        """
        Generic approval step. Override _on_final_approval() for
        document-specific logic (e.g., create payment, generate invoice).
        """
        for rec in self:
            if rec.state == 'submitted':
                next_state = 'verified'
            elif rec.state == 'verified':
                next_state = 'budget_approved'
            elif rec.state == 'budget_approved':
                next_state = 'approved'
            else:
                next_state = 'approved'

            level = ['draft', 'submitted', 'verified', 'budget_approved', 'approved']\
                .index(next_state)
            rec._log_approval_action('approve', level=level)
            rec._mark_activities_done()
            rec.write({'state': next_state})
            if next_state != 'approved' and rec._is_policy_complete_after_state(next_state):
                next_state = 'approved'
                rec.write({'state': next_state})

            if next_state == 'approved':
                rec.write({
                    'approved_by': self.env.uid,
                    'approved_date': fields.Datetime.now(),
                })
                rec._on_final_approval()
                rec.message_post(
                    body=_('Document approved by %s.') % self.env.user.name,
                    subtype_xmlid='mail.mt_note',
                )
            else:
                # Route to next approver
                approver = rec._get_approve_approver()
                if approver:
                    rec._create_approval_activity(
                        approver,
                        summary=_('Approval Required: %s') % rec.display_name,
                        note=_('Please review at level %d.') % level,
                    )

    def action_reject(self, reason=''):
        """Reject the document and return to draft with a mandatory reason."""
        for rec in self:
            if not reason:
                raise UserError(_('A rejection reason is required.'))
            rec._log_approval_action('reject', note=reason)
            rec._mark_activities_done()
            rec.write({
                'state': 'draft',
                'rejection_reason': reason,
            })
            rec.message_post(
                body=_('Document rejected by %s.\nReason: %s') % (
                    self.env.user.name, reason
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_cancel(self):
        """Cancel the document — subclasses should override to close commitments."""
        for rec in self:
            if rec.state == 'approved':
                raise UserError(
                    _('Approved documents cannot be cancelled directly. '
                      'Please contact Finance.')
                )
            rec._log_approval_action('cancel')
            rec._mark_activities_done()
            rec.write({'state': 'cancelled'})
            rec.message_post(
                body=_('Document cancelled by %s.') % self.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_reset_to_draft(self):
        """Reset cancelled/rejected document back to draft."""
        for rec in self:
            if rec.state == 'approved':
                raise UserError(_('Approved documents cannot be reset to draft.'))
            rec._log_approval_action('reset')
            rec.write({'state': 'draft', 'rejection_reason': False})

    # ── Hooks (override in subclasses) ────────────────────────────────

    def _validate_before_submit(self):
        """
        Override to add document-specific validation before submission.
        Raise UserError or ValidationError if invalid.
        """
        pass

    def _get_submit_approver(self):
        """
        Override to return the res.users record who should receive the
        submit activity. Return False to skip activity creation.
        """
        self.ensure_one()
        policy = self._get_approval_policy()
        if policy:
            return policy.get_first_step_user()
        return False

    def _get_approve_approver(self):
        """
        Override to return the next approver after an intermediate approval.
        Return False if no further routing is needed.
        """
        self.ensure_one()
        policy = self._get_approval_policy()
        if policy:
            level_by_state = {
                'submitted': 1,
                'verified': 2,
                'budget_approved': 3,
            }
            step = policy.get_step_for_level(level_by_state.get(self.state, 0))
            if step:
                return step._get_approver_user(self)
        return False

    def _on_final_approval(self):
        """
        Override to execute actions when state reaches 'approved'.
        Examples: create payment, post journal entries, record commitment.
        """
        pass

    def _get_policy_amount(self):
        """Best-effort amount hook used by configurable approval policies."""
        self.ensure_one()
        for field_name in ('amount', 'total_amount', 'amount_total'):
            if field_name in self._fields:
                return self[field_name] or 0.0
        return 0.0

    def _get_approval_policy(self):
        """Return the matching ECS approval policy when ecs_approvals is installed."""
        self.ensure_one()
        if 'ecs.approval.policy' not in self.env:
            return False
        company = getattr(self, 'company_id', False) or self.env.company
        return self.env['ecs.approval.policy'].find_policy(
            self._name,
            company,
            self._get_policy_amount(),
        )

    def _get_group_users(self, group, company=False):
        """Return users of a group across Odoo versions."""
        if not group:
            return self.env['res.users']
        users = getattr(group, 'user_ids', self.env['res.users'])
        if not users and hasattr(group, 'users'):
            users = group.users
        if company:
            users = users.filtered(lambda user: company in user.company_ids)
        return users

    def _is_policy_complete_after_state(self, state):
        """Detect when a policy has no remaining configured step."""
        self.ensure_one()
        policy = self._get_approval_policy()
        if not policy:
            return False
        next_level_by_state = {
            'verified': 2,
            'budget_approved': 3,
        }
        next_level = next_level_by_state.get(state)
        return bool(next_level and not policy.get_step_for_level(next_level))

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_approval_logs_by_record(self):
        persisted_records = self.filtered('id')
        if not persisted_records:
            return {}
        logs = self.env['ecs.approval.log'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', persisted_records.ids),
        ])
        logs_by_record = {record.id: self.env['ecs.approval.log'] for record in persisted_records}
        for log in logs:
            logs_by_record.setdefault(log.res_id, self.env['ecs.approval.log'])
            logs_by_record[log.res_id] |= log
        return logs_by_record

    def _log_approval_action(self, action, level=0, note=''):
        """Write an immutable approval log entry."""
        self.ensure_one()
        self.env['ecs.approval.log'].sudo().create({
            'res_model':   self._name,
            'res_id':      self.id,
            'res_name':    self.display_name,
            'action':      action,
            'level':       level,
            'user_id':     self.env.uid,
            'action_date': fields.Datetime.now(),
            'note':        note or False,
            'company_id':  self.env.company.id,
        })

    def _create_approval_activity(self, user, summary='', note=''):
        """Schedule a To-Do activity on this record for the given user."""
        self.ensure_one()
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_schedule(
            activity_type_id=activity_type.id,
            summary=summary or _('Approval Required'),
            note=note,
            user_id=user.id if hasattr(user, 'id') else user,
        )

    def _mark_activities_done(self):
        """Mark all open approval activities on this record as done."""
        self.ensure_one()
        activities = self.activity_ids.filtered(
            lambda a: a.activity_type_id == self.env.ref('mail.mail_activity_data_todo')
        )
        activities.action_done()
