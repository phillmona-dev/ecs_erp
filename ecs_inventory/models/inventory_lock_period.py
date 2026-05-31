# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcsInventoryLockPeriod(models.Model):
    _name = 'ecs.inventory.lock.period'
    _description = 'ECS Inventory Lock Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(required=True, tracking=True)
    date_from = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    date_to = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('locked', 'Locked'),
        ],
        default='draft',
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    excluded_user_ids = fields.Many2many(
        'res.users',
        'ecs_inventory_lock_period_user_rel',
        'lock_period_id',
        'user_id',
        string='Excluded Users',
        help='Users allowed to validate stock operations inside this locked period.',
    )
    reason = fields.Text()

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for period in self:
            if period.date_from and period.date_to and period.date_from > period.date_to:
                raise ValidationError('Inventory lock period start date cannot be after end date.')

    @api.constrains('date_from', 'date_to', 'company_id', 'state')
    def _check_locked_period_overlap(self):
        for period in self.filtered(lambda rec: rec.state == 'locked'):
            overlapping = self.search(
                [
                    ('id', '!=', period.id),
                    ('state', '=', 'locked'),
                    ('company_id', '=', period.company_id.id),
                    ('date_from', '<=', period.date_to),
                    ('date_to', '>=', period.date_from),
                ],
                limit=1,
            )
            if overlapping:
                raise ValidationError(
                    'Locked inventory periods cannot overlap for the same company.'
                )

    def action_lock(self):
        self.write({'state': 'locked'})

    def action_unlock(self):
        self.write({'state': 'draft'})

    @api.model
    def is_locked(self, date_value, company, user=None):
        if not date_value:
            return False
        operation_date = fields.Date.to_date(date_value)
        company_id = company.id if hasattr(company, 'id') else company
        user = user or self.env.user
        periods = self.sudo().search(
            [
                ('state', '=', 'locked'),
                ('company_id', '=', company_id or self.env.company.id),
                ('date_from', '<=', operation_date),
                ('date_to', '>=', operation_date),
            ]
        )
        for period in periods:
            if user and user.id in period.excluded_user_ids.ids:
                continue
            return period
        return False
