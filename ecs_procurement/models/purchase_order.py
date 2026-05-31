# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ecs_purchase_request_id = fields.Many2one(
        'ecs.purchase.request',
        string='ECS Purchase Request',
        readonly=True,
        copy=False,
        index=True,
    )
    ecs_rfq_id = fields.Many2one(
        'ecs.purchase.rfq',
        string='ECS RFQ',
        readonly=True,
        copy=False,
        index=True,
    )
    ecs_foreign_currency_request_ids = fields.One2many(
        'ecs.foreign.currency.request',
        'purchase_order_id',
        string='Foreign Currency Requests',
        readonly=True,
    )
    ecs_letter_credit_ids = fields.One2many(
        'ecs.letter.credit',
        'purchase_order_id',
        string='Letters of Credit',
        readonly=True,
    )
    ecs_foreign_currency_request_count = fields.Integer(compute='_compute_ecs_import_counts')
    ecs_letter_credit_count = fields.Integer(compute='_compute_ecs_import_counts')

    def _compute_ecs_import_counts(self):
        for order in self:
            order.ecs_foreign_currency_request_count = len(order.ecs_foreign_currency_request_ids)
            order.ecs_letter_credit_count = len(order.ecs_letter_credit_ids)

    def action_create_ecs_foreign_currency_request(self):
        self.ensure_one()
        request = self.env['ecs.foreign.currency.request'].create({
            'purchase_order_id': self.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'requested_amount': self.amount_total,
            'payment_due_date': fields.Date.today(),
            'purpose': self.name,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Foreign Currency Request',
            'res_model': 'ecs.foreign.currency.request',
            'view_mode': 'form',
            'res_id': request.id,
        }

    def action_create_ecs_letter_credit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Letter of Credit',
            'res_model': 'ecs.letter.credit',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_purchase_order_id': self.id,
                'default_company_id': self.company_id.id,
                'default_currency_id': self.currency_id.id,
                'default_lc_amount': self.amount_total,
            },
        }

    def action_view_ecs_foreign_currency_requests(self):
        self.ensure_one()
        action = self.env.ref('ecs_procurement.action_ecs_foreign_currency_request').read()[0]
        action['domain'] = [('id', 'in', self.ecs_foreign_currency_request_ids.ids)]
        return action

    def action_view_ecs_letters_credit(self):
        self.ensure_one()
        action = self.env.ref('ecs_procurement.action_ecs_letter_credit').read()[0]
        action['domain'] = [('id', 'in', self.ecs_letter_credit_ids.ids)]
        return action
