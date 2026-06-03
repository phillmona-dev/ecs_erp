# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('ecs', 'ecs_procurement', 'post_install', '-at_install')
class TestEcsProcurement(TransactionCase):

    def test_request_requires_lines_before_submit(self):
        employee = self.env['hr.employee'].create({
            'name': 'Requester',
            'company_id': self.env.company.id,
        })
        department = self.env['hr.department'].create({
            'name': 'Procurement Test Department',
            'company_id': self.env.company.id,
        })
        request = self.env['ecs.purchase.request'].create({
            'requester_employee_id': employee.id,
            'department_id': department.id,
            'purpose': 'Test request',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(UserError):
            request.action_submit()

    def test_line_rejects_negative_price(self):
        employee = self.env['hr.employee'].create({
            'name': 'Requester',
            'company_id': self.env.company.id,
        })
        department = self.env['hr.department'].create({
            'name': 'Procurement Test Department',
            'company_id': self.env.company.id,
        })
        request = self.env['ecs.purchase.request'].create({
            'requester_employee_id': employee.id,
            'department_id': department.id,
            'purpose': 'Test request',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(ValidationError):
            self.env['ecs.purchase.request.line'].create({
                'request_id': request.id,
                'description': 'Invalid price',
                'quantity': 1.0,
                'estimated_unit_price': -1.0,
            })

    def test_rfq_rejects_deadline_before_date(self):
        employee = self.env['hr.employee'].create({
            'name': 'Requester',
            'company_id': self.env.company.id,
        })
        department = self.env['hr.department'].create({
            'name': 'Procurement Test Department',
            'company_id': self.env.company.id,
        })
        request = self.env['ecs.purchase.request'].create({
            'requester_employee_id': employee.id,
            'department_id': department.id,
            'purpose': 'Test request',
            'company_id': self.env.company.id,
        })
        request.state = 'approved'
        with self.assertRaises(ValidationError):
            self.env['ecs.purchase.rfq'].create({
                'request_id': request.id,
                'company_id': self.env.company.id,
                'rfq_date': '2026-02-02',
                'deadline': '2026-02-01',
            })

    def test_foreign_currency_request_rejects_due_date_before_request(self):
        vendor = self.env['res.partner'].create({
            'name': 'Vendor',
            'supplier_rank': 1,
        })
        order = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'company_id': self.env.company.id,
        })
        employee = self.env['hr.employee'].create({
            'name': 'Requester',
            'company_id': self.env.company.id,
        })
        department = self.env['hr.department'].create({
            'name': 'Procurement Test Department',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(ValidationError):
            self.env['ecs.foreign.currency.request'].create({
                'purchase_order_id': order.id,
                'requester_employee_id': employee.id,
                'department_id': department.id,
                'purpose': 'Foreign payment',
                'requested_amount': 100.0,
                'currency_id': self.env.company.currency_id.id,
                'company_id': self.env.company.id,
                'request_date': '2026-02-02',
                'payment_due_date': '2026-02-01',
            })

    def test_letter_credit_rejects_margin_over_100(self):
        vendor = self.env['res.partner'].create({
            'name': 'Vendor',
            'supplier_rank': 1,
        })
        order = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'company_id': self.env.company.id,
        })
        bank = self.env['res.bank'].create({'name': 'Test Bank'})
        with self.assertRaises(ValidationError):
            self.env['ecs.letter.credit'].create({
                'purchase_order_id': order.id,
                'company_id': self.env.company.id,
                'currency_id': self.env.company.currency_id.id,
                'bank_id': bank.id,
                'branch': 'Main',
                'issue_date': '2026-02-01',
                'lc_amount': 100.0,
                'margin_percent': 120.0,
            })
