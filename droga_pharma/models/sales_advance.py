import random

from odoo import models,fields

class sales_advance(models.TransientModel):
    _inherit='sale.advance.payment.inv'

    def _prepare_down_payment_product_values(self):
        self.ensure_one()
        return {
            'name': 'Down payment',
            'type': 'service',
            'invoice_policy': 'order',
            'company_id': self.env.company.id,
            'property_account_income_id': self.deposit_account_id.id,
            'categ_id':1,
            'default_code':random.randint(0,100)
        }