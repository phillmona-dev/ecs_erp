from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime


class AccountMove(models.Model):
    _inherit = "account.move"

    purpose = fields.Char("Purpose")
    vendor_customer_name = fields.Char("Customer/Vendor Name")
    withholding_no = fields.Char("Withholding Ref", help="Withholding invoice number", store=True)
    withholding_invoice = fields.Boolean("Has Withholding",
                                         help="The transaction has withholding invoice",
                                         compute="is_withholding_transaction", store=True, default=False)
    withholding_invoice_provided = fields.Boolean("Withholding Invoice",
                                                  help="If the transaction has been withheld, the customer needs to provide a withholding invoice",
                                                  default=False)
    withholding_internal_ref = fields.Char("Withholding Internal Ref", help="Withholding Internal Reference")
    sales_initiator = fields.Char("Sales Person", store=True)

    transaction_type = fields.Many2one("account.transaction.type")
    transaction_no = fields.Char("Transaction Number", default='New')
    untaxed_amount_word = fields.Char(
        compute='_compute_amount_word')
    amount_total_word = fields.Char(
        compute='_compute_amount_word')
    tax_amount_word = fields.Char(
        compute='_compute_amount_word')

    withholding_two_percent = fields.Float(
        compute='_compute_withholding_amount')
    withholding_thirty_percent = fields.Float(
        compute='_compute_withholding_amount')

    cost_center = fields.Char(string="Division", store=True, compute='_get_sales_info')
    sales_channel = fields.Char("Sales Channel", store=True, compute='_get_sales_info')
    customer_category = fields.Char("Customer Category", store=True, compute='_get_sales_info')
    due_date_in_days = fields.Integer("Due Days", store=True, compute='update_due_days')

    sales_type = fields.Char("Sales Type", readonly=True)

    # picking list for vendor invoice
    picking_list = fields.One2many('stock.picking', compute='get_picking_list')

    # crv
    crvs = fields.One2many('account.move.crv', 'move_id_crv')



    @api.model
    def create(self, vals):
        # Check withholding
        # vals.update({'withholding_invoice': self.is_withholding_transaction()})
        # generate transaction number
        res = super(AccountMove, self).create(vals)
        return res

    def write(self, vals):
        # Check withholding
        # vals.update({'withholding_invoice': self.is_withholding_transaction()})
        return super(AccountMove, self).write(vals)

    def _compute_amount_word(self):
        for record in self:
            record.untaxed_amount_word = str(
                self.convert_to_word(record.amount_untaxed))
            record.amount_total_word = str(
                self.convert_to_word(record.amount_total))
            if record.withholding_two_percent != 0:
                record.tax_amount_word = str(
                    self.convert_to_word(record.withholding_two_percent))
            elif record.withholding_thirty_percent != 0:
                record.tax_amount_word = str(
                    self.convert_to_word(record.withholding_thirty_percent))

    def _compute_withholding_amount(self):
        tax_amount1 = 0
        tax_amount2 = 0
        for record in self.invoice_line_ids:
            for tax_id in record.tax_ids:
                if tax_id.name == 'Purchase Withholding 2%':
                    tax_amount1 += abs(record.balance * tax_id.amount / 100)
                elif tax_id.name == 'Purchase Withholding 30%':
                    tax_amount2 += abs(record.balance * tax_id.amount / 100)

        self.withholding_two_percent = tax_amount1
        self.withholding_thirty_percent = tax_amount2

    # get sales person
    @api.depends('invoice_line_ids.analytic_distribution')
    def _get_sales_info(self):
        self.sales_initiator = ''
        for record in self:
            if record.move_type == 'out_invoice':
                # get customer category
                record.customer_category = 'Others'
                record.cost_center = "Others"
                record.sales_channel = "Marketing"
                record.customer_category = record.partner_id.cust_type_ext.cust_org_type

                # calculate due days
                delta = datetime.now().date() - record.invoice_date_due
                record.due_date_in_days = delta.days

                # search sales order
                sale_order = self.env["sale.order"].sudo().search([('name', '=', record.invoice_origin)])
                for order in sale_order:
                    record.sales_initiator = order.sales_initiator

                for o in record.invoice_line_ids:
                    if o.analytic_distribution:
                        analytic_distributions = o.analytic_distribution
                        for analytic_distribution_id in analytic_distributions:
                            # search analytic definition table
                            analytic_plans = self.env['account.analytic.account'].search(
                                [('id', '=', analytic_distribution_id)])
                            for analytic_plan in analytic_plans:
                                if analytic_plan.plan_id.complete_name == 'Profit Center':
                                    record.cost_center = analytic_plan.display_name
                                elif analytic_plan.plan_id.complete_name == 'Sales Channel':
                                    record.sales_channel = analytic_plan.display_name
                        break

    @api.depends('invoice_date', 'invoice_payment_term_id')
    def update_due_days(self):
        for record in self:
            # calculate due days
            delta = datetime.now().date() - record.invoice_date_due
            record.due_date_in_days = delta.days

    def update_due_days_all(self):
        records = self.env['account.move'].search(
            [('move_type', '=', 'out_invoice'), ('payment_state', 'in', ('not_paid', 'partial'))])
        for record in records:
            # calculate due days
            delta = datetime.now().date() - record.invoice_date_due
            due_date_in_days = delta.days

            self.env.cr.execute(
                """ update account_move set due_date_in_days=%s where id=%s""",
                (due_date_in_days, record.id))

    def _get_sales_info_obsolete(self):
        self.sales_initiator = ''
        recs = self.env['account.move'].search([('move_type', '=', 'out_invoice')])

        for record in recs:
            if record.move_type == 'out_invoice':

                customer_category = 'Others'
                cost_center = "Others"
                sales_channel = "Marketing"
                sales_initiator = ""

                if record.partner_id.cust_type_ext:
                    customer_category = record.partner_id.cust_type_ext.cust_org_type

                # calculate due days
                delta = datetime.now().date() - record.invoice_date_due
                due_date_in_days = delta.days

                # search sales order
                sale_order = self.env["sale.order"].sudo().search([('name', '=', record.invoice_origin)])
                for order in sale_order:
                    sales_initiator = order.sales_initiator

                    """# get cost center
                    if order.tender_origin_form_tender:
                        sales_channel = "Tender"
                    else:
                        sales_channel = "Marketing"

                    if order.order_type:
                        cost_center = order.order_type"""

                for o in record.invoice_line_ids:

                    if o.analytic_distribution:
                        analytic_distributions = o.analytic_distribution
                        for analytic_distribution_id in analytic_distributions:
                            # search analytic definition table
                            analytic_plans = self.env['account.analytic.account'].search(
                                [('id', '=', analytic_distribution_id)])
                            for analytic_plan in analytic_plans:
                                if analytic_plan.plan_id.complete_name == 'Profit Center':
                                    cost_center = analytic_plan.display_name
                                elif analytic_plan.plan_id.complete_name == 'Sales Channel':
                                    sales_channel = analytic_plan.display_name
                        break

                self.env.cr.execute(
                    """ update account_move set customer_category=%s,cost_center=%s,sales_channel=%s,due_date_in_days=%s,sales_initiator=%s where id=%s""",
                    (
                        customer_category, cost_center, sales_channel, due_date_in_days, sales_initiator, record.id))

    # check if the transaction has withholding transaction
    @api.depends("invoice_line_ids.tax_ids")
    def is_withholding_transaction(self):
        has_withholding_line = False
        for record in self.invoice_line_ids:
            for tax in record.tax_ids:
                if tax.tax_group_id.name == 'Withholding':
                    has_withholding_line = True
                    break
        self.withholding_invoice = has_withholding_line

    # get picking list from purchase order
    def get_picking_list(self):

        for record in self:
            record.picking_list = None
            if record.move_type in ('out_invoice', 'in_invoice'):
                # search picking list using purchase order name
                picking_lists = self.env['stock.picking'].search([('origin', '=', record.invoice_origin)])
                if picking_lists:
                    record.picking_list = picking_lists

    # Generate withholding reference
    def generate_withholding_ref(self):
        # get sequence number for each company
        for record in self:
            if record.withholding_internal_ref:
                raise ValidationError("Internal withholding reference already generated")
            self_comp = self.with_company(record.company_id)

            record.withholding_internal_ref = self_comp.env['ir.sequence'].next_by_code(
                'withholding.internal.reference') or '/'

    @api.constrains('crvs')
    def validate_crv(self):
        # get total amount
        total_amount = abs(self.amount_untaxed_signed)
        total_amount_crv = 0
        for record in self.crvs:
            # sum crv amount
            total_amount_crv += record.amount

        if total_amount_crv > total_amount:
            raise ValidationError("You can't print CRV amount greater than the invoice amount")

    def convert_to_word(self, num):
        num_strings = str(num)
        numbers = num_strings.split('.')

        word = self.int_to_word(int(numbers[0])) + ' birr'

        if len(numbers) == 2:
            if int(numbers[1]) != 0:
                word = self.int_to_word(int(numbers[0])) + ' birr and ' + self.int_to_word(int(numbers[1])) + ' cents'

        return word.capitalize()

    def int_to_word(self, num):
        d = {0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
             6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
             11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen',
             15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen',
             19: 'nineteen', 20: 'twenty',
             30: 'thirty', 40: 'forty', 50: 'fifty', 60: 'sixty',
             70: 'seventy', 80: 'eighty', 90: 'ninety'}
        k = 1000
        m = k * 1000
        b = m * 1000
        t = b * 1000

        assert (0 <= num)

        if (num < 20):
            return d[num]

        if (num < 100):
            if num % 10 == 0:
                return d[num]
            else:
                return d[num // 10 * 10] + '-' + d[num % 10]

        if (num < k):
            if num % 100 == 0:
                return d[num // 100] + ' hundred'
            else:
                return d[num // 100] + ' hundred ' + self.int_to_word(num % 100)

        if (num < m):
            if num % k == 0:
                return self.int_to_word(num // k) + ' thousand'
            else:
                return self.int_to_word(num // k) + ' thousand ' + self.int_to_word(num % k)

        if (num < b):
            if (num % m) == 0:
                return self.int_to_word(num // m) + ' million'
            else:
                return self.int_to_word(num // m) + ' million ' + self.int_to_word(num % m)

        if (num < t):
            if (num % b) == 0:
                return self.int_to_word(num // b) + ' billion'
            else:
                return self.int_to_word(num // b) + ' billion ' + self.int_to_word(num % b)

        if (num % t == 0):
            return self.int_to_word(num // t) + ' trillion'
        else:
            return self.int_to_word(num // t) + ' trillion ' + self.int_to_word(num % t)

        raise AssertionError('num is too large: %s' % str(num))


# CRV document tracking
class AccountCrv(models.Model):
    _name = 'account.move.crv'

    move_id_crv = fields.Many2one('account.move')
    crv_ref = fields.Char("CRV Reference", required=True)
    amount = fields.Float("Amount", required=True)
    is_crv_document_printed = fields.Boolean("Document Printed")
    payment_description = fields.Char("Payment Description")
    amount_word = fields.Char("Amount Word", compute='_compute_amount_word')

    def _compute_amount_word(self):
        for record in self:
            record.amount_word = self.env['account.move'].convert_to_word(record.amount)

    @api.constrains('crv_ref')
    def check_crv_ref(self):
        for record in self:
            # search crv ref in the database
            crv_count = self.env['account.move.crv'].search_count([('crv_ref', '=', record.crv_ref)])
            if crv_count > 1:
                raise ValidationError(
                    'CRV Reference already registered in the system, you can''t use one reference multiple times')
