# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ecs_transaction_type_id = fields.Many2one(
        'ecs.inventory.transaction.type',
        string='ECS Transaction Type',
        check_company=True,
        tracking=True,
    )
    ecs_request_reference = fields.Char(string='ECS Request Reference', copy=False, tracking=True)
    ecs_inventory_request_id = fields.Many2one(
        'ecs.inventory.request',
        string='ECS Inventory Request',
        copy=False,
        index=True,
    )
    ecs_locked_period_id = fields.Many2one(
        'ecs.inventory.lock.period',
        string='Locked Period',
        compute='_compute_ecs_locked_period',
    )
    ecs_is_locked_period = fields.Boolean(
        string='In Locked Period',
        compute='_compute_ecs_locked_period',
    )

    @api.depends('scheduled_date', 'date_done', 'company_id')
    def _compute_ecs_locked_period(self):
        lock_period_model = self.env['ecs.inventory.lock.period']
        for picking in self:
            operation_date = fields.Date.to_date(
                picking.date_done or picking.scheduled_date or fields.Datetime.now()
            )
            locked_period = lock_period_model.is_locked(
                operation_date,
                picking.company_id,
                self.env.user,
            )
            picking.ecs_locked_period_id = locked_period.id if locked_period else False
            picking.ecs_is_locked_period = bool(locked_period)

    def _check_ecs_inventory_period_unlocked(self):
        lock_period_model = self.env['ecs.inventory.lock.period']
        for picking in self:
            operation_date = fields.Date.to_date(
                picking.date_done or picking.scheduled_date or fields.Datetime.now()
            )
            locked_period = lock_period_model.is_locked(
                operation_date,
                picking.company_id,
                self.env.user,
            )
            if locked_period:
                raise UserError(
                    'Inventory transactions are locked for %(company)s from %(start)s to %(end)s.'
                    % {
                        'company': picking.company_id.display_name,
                        'start': locked_period.date_from,
                        'end': locked_period.date_to,
                    }
                )

    def button_validate(self):
        self._check_ecs_inventory_period_unlocked()
        return super().button_validate()

    def _action_done(self):
        self._check_ecs_inventory_period_unlocked()
        return super()._action_done()
