from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError
import textwrap


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    transaction_type = fields.Many2one("account.transaction.type")
    payment_request_id = fields.Many2one("droga.account.payment.request")
    purpose = fields.Char("Purpose")

    check_due_date = fields.Date("Check Due Date")
    vendor_supplier = fields.Char("Vendor/Customer Name")

    is_check_printed = fields.Selection([('Yes', 'Yes'), ('No', 'No')], default='No')

    first_line_amount_word = fields.Char(compute="_compute_check_print_word")
    second_line_amount_word = fields.Char(compute="_compute_check_print_word")
    third_line_amount_word = fields.Char(compute="_compute_check_print_word")

    amount_total_word = fields.Char(
        compute='_compute_amount_word')

    category = fields.Char("Customer Category")
    division = fields.Char("Division")
    sales_channel = fields.Char("Sales Channel")

    @api.model
    def create(self, vals):
        # get divison and sales channel

        # search account move
        ref = vals.get('ref')  # Safely get 'ref' to avoid KeyError
        if ref:
            account_move = self.env["account.move"].sudo().search([('name', '=', ref)])
            for o in account_move.invoice_line_ids:
                if o.analytic_distribution:
                    analytic_distributions = o.analytic_distribution
                    for analytic_distribution_id in analytic_distributions:
                        # search analytic definition table
                        analytic_plans = self.env['account.analytic.account'].search(
                            [('id', '=', analytic_distribution_id)])
                        for analytic_plan in analytic_plans:
                            if analytic_plan.plan_id.complete_name == 'Profit / Cost Center':
                                vals.update({'division': analytic_plan.display_name})
                            elif analytic_plan.plan_id.complete_name == 'Sales Channel':
                                vals.update({'sales_channel': analytic_plan.display_name})
                    break

        res = super(AccountPayment, self).create(vals)
        # enable when manual transaction number stops
        self.generate_transaction_type(res)
        return res

    @api.onchange('transaction_type', 'journal_id', 'payment_type')
    def _load_transaction_type(self):
        res = {}
        for record in self:
            if record.payment_type == "outbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "outbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Cash')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Cash')]}

        return res

    # generate transaction number for check payment voucher,petty cash and bank deposit
    def generate_transaction_type(self, res):
        transaction_type_no = None
        # search record from account.move
        for record in res:
            # Payment using cash
            if record.payment_type == 'outbound' and record.journal_id.type == "cash":
                transaction_type_no = self.get_transaction_no("Payment", "Cash", res)
            elif record.payment_type == 'outbound' and record.journal_id.type == "bank":
                transaction_type_no = self.get_transaction_no("Payment", "Bank", res)  # Check payment voucher
            elif record.payment_type == 'inbound' and record.journal_id.type == "cash":
                transaction_type_no = self.get_transaction_no("Receipt", "Cash", res)
            elif record.payment_type == 'inbound' and record.journal_id.type == "bank":
                transaction_type_no = self.get_transaction_no("Receipt", "Bank", res)

                # update account move
            record.move_id.write({'transaction_type': transaction_type_no['transaction_type'],
                                  'transaction_no': transaction_type_no['transaction_no']})

    def get_transaction_no(self, transaction_type, payment_method, res):
        transaction = {'transaction_type': '-', 'transaction_no': 'New'}
        payment_date = res.date
        fiscal_year = self.env['account.fiscal.year'].search(
            [('date_from', '<=', payment_date), ('date_to', '>=', payment_date),
             ('company_id', '=', res.company_id.id)])

        sequence = None
        if fiscal_year:
            # get transaction type
            transaction_types = self.env["account.transaction.type"].search(
                [('payment_method', '=', payment_method), ('transaction_type', '=', transaction_type),
                 ('company_id', '=', res.company_id.id)])
            for record in transaction_types.posting_cycles:
                if record.fiscal_year.id == fiscal_year.id:
                    # get sequence
                    sequence = record.sequence

            for rec in transaction_types:
                transaction_type = rec

            if sequence:
                # generate new sequence
                # get sequence number for each company
                # transaction_no = self.env['ir.sequence'].next_by_code(sequence.code) or '/'
                transaction_no = sequence.next_by_id()
                # update transaction
                transaction.update({'transaction_type': transaction_type, 'transaction_no': transaction_no})
                return transaction
            else:
                raise ValidationError(
                    "Sequence is not defined for the transaction type")

    def print_check(self):
        res1 = self.env.ref('droga_finance.droga_account_check_printout_cbe_action').report_action(self)
        return res1

    def _compute_amount_word(self):
        for record in self:
            record.amount_total_word = self.env['account.move'].convert_to_word(record.amount)

    def _compute_check_print_word(self):
        # get journal id
        for record in self:
            record.first_line_amount_word = ''
            record.second_line_amount_word = ''
            record.third_line_amount_word = ''
            check_setting = record.journal_id.check_setting

            if check_setting:
                wrapper1 = textwrap.TextWrapper(width=check_setting.amount_word_width)
                wrapper2 = textwrap.TextWrapper(width=check_setting.amount_word_width1)

                first_word_list = wrapper1.wrap(text=record.amount_total_word)

                if len(first_word_list) == 1:
                    record.first_line_amount_word = first_word_list[0]
                elif len(first_word_list) > 1:
                    second_word = first_word_list[1:]
                    second_word = ' '.join(second_word)

                    second_word_list = wrapper2.wrap(text=second_word)

                    if len(second_word_list) > 1:
                        record.first_line_amount_word = first_word_list[0]
                        record.second_line_amount_word = second_word_list[0]

                        third_items = second_word_list[1:]
                        t_word = ' '.join(third_items)
                        record.third_line_amount_word = t_word

                    else:
                        record.first_line_amount_word = first_word_list[0]
                        second_items = first_word_list[1:]

                        s_word = ' '.join(second_items)
                        record.second_line_amount_word = s_word

    def update_sale_info(self):
        Payment = self.env['account.payment'].with_context(prefetch_fields=False)
        Analytic = self.env['account.analytic.account']

        payments = Payment.search([
            ('division', 'in', [False, '']),
            ('payment_type', '=', 'inbound'),
            ('reconciled_invoice_ids', '!=', False),
        ], limit=10000)

        if not payments:
            return

        # -------- Prefetch related records --------
        payments.mapped('partner_id.cust_type_ext')
        invoices = payments.mapped('reconciled_invoice_ids')
        lines = invoices.mapped('invoice_line_ids')

        # Collect all analytic IDs once
        analytic_ids = set()
        for line in lines:
            if line.analytic_distribution:
                analytic_ids.update(map(int, line.analytic_distribution.keys()))

        analytic_map = {
            a.id: a
            for a in Analytic.browse(list(analytic_ids)).with_context(prefetch_fields=False)
        }

        # -------- Main loop --------
        for payment in payments:
            vals = {
                'category': 'Others',
                'division': 'Others',
                'sales_channel': 'Marketing',
            }

            # Customer category
            cust = payment.partner_id.cust_type_ext
            if cust and cust.cust_org_type:
                vals['category'] = cust.cust_org_type

            invoice = payment.reconciled_invoice_ids[:1]
            if not invoice:
                payment.write(vals)
                continue

            line = invoice.invoice_line_ids[:1]
            if not line or not line.analytic_distribution:
                payment.write(vals)
                continue

            for aid in map(int, line.analytic_distribution.keys()):
                analytic = analytic_map.get(aid)
                if not analytic:
                    continue

                plan = analytic.plan_id.complete_name
                if plan == 'Profit / Cost Center':
                    vals['division'] = analytic.display_name
                elif plan == 'Sales Channel':
                    vals['sales_channel'] = analytic.display_name

            payment.write(vals)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    transaction_type = fields.Many2one("account.transaction.type")

    @api.onchange('transaction_type', 'journal_id', 'payment_type')
    def _load_transaction_type(self):
        res = {}
        for record in self:
            if record.payment_type == "outbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "outbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Payment'), ('payment_method', '=', 'Cash')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'bank':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Bank')]}
            elif record.payment_type == "inbound" and record.journal_id.type == 'cash':
                res['domain'] = {'transaction_type': [
                    ('transaction_type', '=', 'Receipt'), ('payment_method', '=', 'Cash')]}

        return res
