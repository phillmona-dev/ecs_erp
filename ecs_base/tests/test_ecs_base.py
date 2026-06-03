# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('ecs', 'ecs_base', 'post_install', '-at_install')
class TestEcsCurrencyMixin(TransactionCase):

    def setUp(self):
        super().setUp()
        self.mixin = self.env['ecs.currency.word.mixin']

    def test_whole_birr_no_cents(self):
        result = self.mixin.amount_to_word(1500.00)
        self.assertIn('One Thousand Five Hundred', result)
        self.assertIn('Birr Only', result)
        self.assertNotIn('Cents', result)

    def test_birr_with_cents(self):
        result = self.mixin.amount_to_word(1500.50)
        self.assertIn('Fifty Cents', result)
        self.assertNotIn('Only', result)

    def test_zero(self):
        result = self.mixin.amount_to_word(0.0)
        self.assertIn('Zero', result)

    def test_large_amount(self):
        result = self.mixin.amount_to_word(1_250_000.00)
        self.assertIn('Million', result)
        self.assertIn('Two Hundred', result)

    def test_one_cent(self):
        result = self.mixin.amount_to_word(0.01)
        self.assertIn('One Cents', result)

    def test_nineteen(self):
        result = self.mixin._int_to_word(19)
        self.assertEqual(result, 'Nineteen')

    def test_hundred(self):
        result = self.mixin._int_to_word(100)
        self.assertEqual(result, 'One Hundred')

    def test_twenty_one(self):
        result = self.mixin._int_to_word(21)
        self.assertEqual(result, 'Twenty One')


@tagged('ecs', 'ecs_base', 'post_install', '-at_install')
class TestEcsSequenceService(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['ecs.sequence.service']
        self.company = self.env.company

    def test_generates_formatted_reference(self):
        from datetime import date
        ref = self.service.get_transaction_no('CPV', date(2024, 1, 15), self.company.id)
        # Jan 15 2024 → Ethiopian year 2016 (before Sept 11)
        self.assertTrue(ref.startswith('CPV/2016/'))

    def test_generates_sequential_numbers(self):
        from datetime import date
        ref1 = self.service.get_transaction_no('PR', date(2024, 3, 1), self.company.id)
        ref2 = self.service.get_transaction_no('PR', date(2024, 3, 1), self.company.id)
        num1 = int(ref1.split('/')[-1])
        num2 = int(ref2.split('/')[-1])
        self.assertEqual(num2, num1 + 1)

    def test_ethiopian_year_before_sept11(self):
        from datetime import date
        year = self.service._gregorian_to_ethiopian_year(date(2024, 9, 10))
        self.assertEqual(year, 2016)  # Before Sept 11 → subtract 8

    def test_ethiopian_year_after_sept11(self):
        from datetime import date
        year = self.service._gregorian_to_ethiopian_year(date(2024, 9, 11))
        self.assertEqual(year, 2017)  # From Sept 11 → subtract 7

    def test_different_companies_independent_sequences(self):
        from datetime import date
        company_b = self.env['res.company'].create({'name': 'Test Company B'})
        ref_a = self.service.get_transaction_no('BPV', date(2024, 6, 1), self.company.id)
        ref_b = self.service.get_transaction_no('BPV', date(2024, 6, 1), company_b.id)
        # Both start at 00001 independently
        self.assertTrue(ref_a.endswith('00001'))
        self.assertTrue(ref_b.endswith('00001'))


@tagged('ecs', 'ecs_base', 'post_install', '-at_install')
class TestEcsApprovalMixin(TransactionCase):
    """
    Tests use ecs.approval.log as a concrete proxy since the mixin
    itself is abstract. Real workflow tests live in ecs_finance/tests.
    """

    def test_approval_log_cannot_be_deleted(self):
        from odoo.exceptions import UserError
        log = self.env['ecs.approval.log'].sudo().create({
            'res_model': 'test.model',
            'res_id': 1,
            'action': 'submit',
        })
        with self.assertRaises(UserError):
            log.unlink()
