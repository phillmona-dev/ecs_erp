# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('ecs', 'ecs_payroll', 'post_install', '-at_install')
class TestEcsPayroll(TransactionCase):

    def test_payroll_rate_lookup(self):
        self.env['ecs.payroll.rate'].create({
            'name': 'Test Rate',
            'code': 'TST',
            'rate': 12.5,
            'date_from': '2026-01-01',
            'company_id': self.env.company.id,
        })
        rate = self.env['ecs.payroll.rate'].get_rate('TST', date='2026-02-01', company_id=self.env.company.id)
        self.assertEqual(rate, 12.5)

    def test_tax_bracket_calculates_configured_amount(self):
        self.env['ecs.payroll.tax.bracket'].create({
            'date_from': '2026-01-01',
            'lower_bound': 0.0,
            'upper_bound': 1000.0,
            'rate': 10.0,
            'deduction': 50.0,
            'company_id': self.env.company.id,
        })
        tax = self.env['ecs.payroll.tax.bracket'].compute_tax(
            900.0,
            date='2026-02-01',
            company_id=self.env.company.id,
        )
        self.assertEqual(tax, 40.0)

    def test_period_rejects_invalid_dates(self):
        with self.assertRaises(ValidationError):
            self.env['ecs.payroll.period'].create({
                'name': 'Invalid Period',
                'date_start': '2026-02-01',
                'date_end': '2026-01-31',
                'company_id': self.env.company.id,
            })

    def test_variable_input_rejects_negative_amount(self):
        period = self.env['ecs.payroll.period'].create({
            'name': 'January 2026',
            'date_start': '2026-01-01',
            'date_end': '2026-01-31',
            'company_id': self.env.company.id,
        })
        employee = self.env['hr.employee'].create({
            'name': 'Payroll Employee',
            'company_id': self.env.company.id,
        })
        input_type = self.env['ecs.payroll.input.type'].create({
            'name': 'Test Input',
            'code': 'TSTIN',
        })
        with self.assertRaises(ValidationError):
            self.env['ecs.payroll.variable.input'].create({
                'employee_id': employee.id,
                'period_id': period.id,
                'input_type_id': input_type.id,
                'amount': -1.0,
                'company_id': self.env.company.id,
            })
