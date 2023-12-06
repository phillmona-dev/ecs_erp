from datetime import date

from odoo import models, fields, api

class pharma_credit(models.Model):
    _inherit = 'res.partner'
    cust_credit_limit_pharma = fields.Float(string='Credit limit', tracking=True)
    unsettled_amount_pharma = fields.Monetary(compute='_compute_balance_pharma', string='Unsettled amount')
    available_amount_pharma = fields.Float(string='Credit balance', compute='_compute_balance_pharma')
    allowed_credit_terms=fields.Many2many('account.payment.term')
    manual_sales_extension_date=fields.Date('Manual sales extension date',tracking=True)

    @api.depends('debit', 'credit')
    def _compute_balance_pharma(self):
        for record in self:
            if record.id in [15390, 15488]:
                matured_invoices = []
            elif record.vat != '0000000000':
                matured_invoices = self.env['account.move'].search(
                    [('state', '=', 'posted'), ('journal_id.type', '=', 'sale'),('cost_center','like','Pharmacy%'),
                     ('payment_state', 'in', ['not_paid', 'partial']), ('partner_id.vat', '=', record.vat), '|',
                     ('partner_id.active', '=', True), ('partner_id.active', '=', False)])
            else:
                matured_invoices = self.env['account.move'].search(
                    [('state', '=', 'posted'), ('journal_id.type', '=', 'sale'),('cost_center','like','Pharmacy%'),
                     ('payment_state', 'in', ['not_paid', 'partial']), ('partner_id', '=', record.id), '|',
                     ('partner_id.active', '=', True), ('partner_id.active', '=', False)])
            tot_amount = 0
            for mi in matured_invoices:
                tot_amount = tot_amount + (
                    mi['amount_total_signed'] if mi['amount_residual'] == 0 else mi['amount_residual'])
            record.unsettled_amount_pharma = tot_amount
            # record.unsettled_amount = record.credit - record.debit

            record.available_amount_pharma = record.cust_credit_limit_pharma - record.unsettled_amount_pharma

