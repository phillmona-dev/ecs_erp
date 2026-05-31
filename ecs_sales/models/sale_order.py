# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_cust_credit_limit = fields.Float(
        related='partner_id.cust_credit_limit',
        string='Customer Credit Limit',
        readonly=True,
    )
    partner_available_amount = fields.Float(
        related='partner_id.available_amount',
        string='Available Credit Balance',
        readonly=True,
    )

    @api.model
    def action_confirm(self):
        """
        Validate Customer Credit Limit and Overdue Invoices before confirmation.
        """
        today = fields.Date.today()
        for order in self:
            partner = order.partner_id
            company = order.company_id

            # ── Check 1: Matured (overdue) unpaid invoices ────────────────────
            # Block confirmation if customer has ANY posted unpaid/partially paid invoice
            # with a due date in the past for this company.
            overdue_invoices = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', today),
                ('company_id', '=', company.id),
            ])
            if overdue_invoices:
                invoice_names = ", ".join(overdue_invoices.mapped('name'))
                raise ValidationError(_(
                    "Cannot confirm Sales Order '%s' because customer '%s' has overdue unpaid invoices: %s. "
                    "Please settle outstanding balances first."
                ) % (order.name, partner.name, invoice_names))

            # ── Check 2: Credit Limit Exceeded ──────────────────────────────
            if order.payment_term_id and order.payment_term_id.apply_credit_limit:
                # Fetch available credit limit (which is already company-isolated)
                available_credit = partner.with_company(company).available_amount
                order_amount = order.amount_total

                if available_credit < order_amount:
                    raise ValidationError(_(
                        "Cannot confirm Sales Order '%s' due to credit limit violation.\n"
                        "Customer Available Credit: %s %s\n"
                        "Order Total: %s %s\n"
                        "Required Credit: %s %s"
                    ) % (
                        order.name,
                        available_credit, company.currency_id.symbol,
                        order_amount, company.currency_id.symbol,
                        order_amount - available_credit, company.currency_id.symbol
                    ))

        return super(SaleOrder, self).action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'product_uom_qty', 'order_id.partner_id', 'order_id.payment_term_id')
    def _compute_discount(self):
        """
        Compute discount percentage automatically using ECS Discount Rules.
        """
        super(SaleOrderLine, self)._compute_discount()
        for line in self:
            if not line.product_id or not line.order_id:
                continue

            # Fetch the discount from our rule engine
            rule_discount = self.env['ecs.sales.discount.rule'].get_discount(
                partner=line.order_id.partner_id,
                product=line.product_id,
                payment_term=line.order_id.payment_term_id,
                date=line.order_id.date_order.date() if line.order_id.date_order else fields.Date.today(),
                company_id=line.company_id.id,
            )

            # Apply if a rule is found and is higher than standard pricelist discount
            if rule_discount > 0.0:
                line.discount = rule_discount
