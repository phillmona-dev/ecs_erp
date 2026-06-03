# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('ecs', 'ecs_hr', 'post_install', '-at_install')
class TestEcsHr(TransactionCase):

    def test_employee_code_is_generated(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': self.env.company.id,
        })
        self.assertTrue(employee.employee_code)
        self.assertTrue(employee.employee_code.startswith('EMP/'))

    def test_division_is_company_scoped(self):
        division = self.env['ecs.hr.division'].create({
            'name': 'Test Division',
            'code': 'TD',
            'company_id': self.env.company.id,
        })
        self.assertEqual(division.company_id, self.env.company)

    def test_overtime_hours_must_be_positive(self):
        employee = self.env['hr.employee'].create({
            'name': 'Overtime Employee',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(ValidationError):
            self.env['ecs.hr.overtime.report'].create({
                'company_id': self.env.company.id,
                'employee_id': employee.id,
                'date': '2026-01-01',
                'overtime_hours': 0,
                'reason': 'Test',
            })
