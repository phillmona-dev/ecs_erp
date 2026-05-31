# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestEcsInventory(TransactionCase):
    def test_lock_period_requires_valid_date_range(self):
        with self.assertRaises(ValidationError):
            self.env['ecs.inventory.lock.period'].create(
                {
                    'name': 'Invalid lock period',
                    'date_from': '2026-02-10',
                    'date_to': '2026-02-01',
                    'company_id': self.env.company.id,
                }
            )

    def test_locked_period_detector_respects_company(self):
        date_from = fields.Date.to_date(fields.Date.today())
        period = self.env['ecs.inventory.lock.period'].create(
            {
                'name': 'Month end close',
                'date_from': date_from,
                'date_to': date_from + timedelta(days=1),
                'state': 'locked',
                'company_id': self.env.company.id,
            }
        )
        locked_period = self.env['ecs.inventory.lock.period'].is_locked(
            date_from,
            self.env.company,
            self.env.user,
        )
        self.assertEqual(locked_period, period)

    def test_inventory_request_requires_lines_before_submit(self):
        request = self.env['ecs.inventory.request'].create(
            {
                'purpose': 'Department stock transfer',
                'company_id': self.env.company.id,
                'picking_type_id': self.env['stock.picking.type'].search(
                    [('company_id', 'in', [False, self.env.company.id])],
                    limit=1,
                ).id,
            }
        )
        with self.assertRaises(UserError):
            request.action_submit()
