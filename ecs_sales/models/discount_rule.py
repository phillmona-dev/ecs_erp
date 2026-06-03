# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class EcsSalesDiscountRule(models.Model):
    """
    Multi-Company Sales Discount Rules.
    Defines percentage discounts based on combinations of:
    - Customer
    - Product / Product Category
    - Payment Term
    """
    _name = 'ecs.sales.discount.rule'
    _description = 'Sales Discount Rule'
    _order = 'company_id, sequence, discount_percentage desc'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, ondelete='restrict'
    )

    # ── Match Criteria ────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        help="Leave blank to apply to all customers."
    )
    product_id = fields.Many2one(
        'product.product', string='Product',
        help="Leave blank to apply to all products."
    )
    categ_id = fields.Many2one(
        'product.category', string='Product Category',
        help="Leave blank to apply to all categories. If a product is specified, category is ignored."
    )
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Term',
        help="Leave blank to apply to all payment terms."
    )

    # ── Validity and value ───────────────────────────────────────────
    discount_percentage = fields.Float(
        string='Discount (%)', required=True, digits=(5, 2), default=0.0
    )
    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    date_to = fields.Date(string='End Date')
    active = fields.Boolean(default=True)

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        for rule in self:
            if not (0.0 <= rule.discount_percentage <= 100.0):
                raise ValidationError(_('Discount percentage must be between 0 and 100.'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rule in self:
            if rule.date_to and rule.date_from > rule.date_to:
                raise ValidationError(_('End Date cannot be before Start Date.'))

    @api.model
    def get_discount(self, partner, product, payment_term, date=None, company_id=None):
        """
        Search active discount rules and return the highest applicable discount percentage.

        :param partner: res.partner record
        :param product: product.product record
        :param payment_term: account.payment.term record
        :param date: date (defaults to today)
        :param company_id: int (defaults to current company)
        :return: float — discount percentage
        """
        date = date or fields.Date.today()
        company_id = company_id or self.env.company.id

        # Build domain to match any active rule for this company and date range
        domain = [
            ('company_id', '=', company_id),
            ('active', '=', True),
            ('date_from', '<=', date),
            '|', ('date_to', '=', False), ('date_to', '>=', date),
        ]

        rules = self.search(domain)
        if not rules:
            return 0.0

        applicable_discounts = []
        for rule in rules:
            # Check Partner match
            if rule.partner_id and rule.partner_id != partner:
                continue

            # Check Product / Category match
            if rule.product_id:
                if rule.product_id != product:
                    continue
            elif rule.categ_id:
                # Walk up category hierarchy to match category or its parents
                categ = product.categ_id
                matched = False
                while categ:
                    if categ == rule.categ_id:
                        matched = True
                        break
                    categ = categ.parent_id
                if not matched:
                    continue

            # Check Payment Term match
            if rule.payment_term_id and rule.payment_term_id != payment_term:
                continue

            applicable_discounts.append(rule.discount_percentage)

        return max(applicable_discounts) if applicable_discounts else 0.0
