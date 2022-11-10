from odoo import models, fields, api
from odoo.exceptions import ValidationError


class cust_credit_limit(models.Model):
    _inherit='res.partner'
    cust_credit_limit = fields.Float(string='Credit limit')
    unsettled_amount = fields.Float(string='Unsettled amount')
    available_amount = fields.Float(string='Available credit',compute='_compute_cust_unsetlled_amount')

    def _compute_cust_unsetlled_amount(self):
        for rec in self:
            rec.available_amount = rec.cust_credit_limit-rec.unsettled_amount

