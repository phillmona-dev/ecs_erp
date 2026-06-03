# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class EcsApprovalLog(models.Model):
    """Immutable audit log entry for each approval action."""
    _name = 'ecs.approval.log'
    _description = 'ECS Approval Log'
    _order = 'action_date desc, id desc'
    _rec_name = 'action_date'

    res_model = fields.Char('Document Model', required=True, readonly=True, index=True)
    res_id = fields.Integer('Document ID', required=True, readonly=True, index=True)
    res_name = fields.Char('Document Reference', readonly=True)
    action = fields.Selection([
        ('submit',          'Submitted'),
        ('approve',         'Approved'),
        ('reject',          'Rejected'),
        ('cancel',          'Cancelled'),
        ('reset',           'Reset to Draft'),
        ('budget_approve',  'Budget Approved'),
    ], string='Action', required=True, readonly=True)
    level = fields.Integer('Approval Level', readonly=True)
    user_id = fields.Many2one('res.users', 'By', readonly=True,
                              default=lambda self: self.env.uid)
    action_date = fields.Datetime('At', readonly=True,
                                  default=fields.Datetime.now)
    note = fields.Text('Note / Reason', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True,
                                 default=lambda self: self.env.company, index=True)

    def unlink(self):
        raise UserError(_('Approval log entries cannot be deleted — they are audit records.'))
