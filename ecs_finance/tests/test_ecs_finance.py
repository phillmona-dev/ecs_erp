# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('ecs', 'ecs_finance', 'post_install', '-at_install')
class TestEcsFinance(TransactionCase):

    def test_transaction_type_generates_company_reference(self):
        transaction_type = self.env['ecs.finance.transaction.type'].create({
            'name': 'Test Payment Voucher',
            'code': 'TPV',
            'company_id': self.env.company.id,
            'transaction_category': 'payment',
        })
        reference = transaction_type.get_next_reference()
        self.assertTrue(reference.startswith('TPV/'))

    def test_withholding_amount_uses_configured_rate(self):
        config = self.env['ecs.finance.withholding.config'].new({
            'name': 'Test Withholding 2%',
            'company_id': self.env.company.id,
            'partner_type': 'goods',
            'rate': 2.0,
        })
        self.assertEqual(config.compute_withholding_amount(1000.0), 20.0)

    def test_payment_request_has_generated_reference(self):
        partner = self.env['res.partner'].create({'name': 'Test Payee'})
        request = self.env['ecs.finance.payment.request'].create({
            'company_id': self.env.company.id,
            'purpose': 'Test payment request',
            'amount': 100.0,
            'payee_id': partner.id,
        })
        self.assertNotEqual(request.name, 'New')
        self.assertTrue(request.name.startswith('PMR/'))
