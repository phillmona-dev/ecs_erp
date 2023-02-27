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
    sales_initiator = fields.Char("Sales Person", compute="_get_sales_person")

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

    cost_center = fields.Char("Cost Center", compute='_get_sales_person', default="Data Not Found")
    customer_category = fields.Char(compute="_get_sales_person", default="Others")

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
                self.convert_to_word1(record.amount_untaxed))
            record.amount_total_word = str(
                self.convert_to_word1(record.amount_total))
            if record.withholding_two_percent != 0:
                record.tax_amount_word = str(
                    self.convert_to_word1(record.withholding_two_percent))
            elif record.withholding_thirty_percent != 0:
                record.tax_amount_word = str(
                    self.convert_to_word1(record.withholding_thirty_percent))

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
    def _get_sales_person(self):
        self.sales_initiator = ''
        for record in self:
            # get customer category
            record.customer_category = 'Others'
            record.cost_center = "Others"
            record.customer_category = record.partner_id.cust_type_ext.cust_org_type
            # search sales order
            sale_order = self.env["sale.order"].sudo().search([('name', '=', record.invoice_origin)])
            for order in sale_order:
                record.sales_initiator = order.sales_initiator

                # get cost center

                if order.tender_origin_form_tender:
                    record.cost_center = "Tender"
                else:
                    record.cost_center = "Marketing"

    def convert_to_word1(self, number):
        number = str(number)
        int_side = number
        dec_side = ''
        for i in range(0, len(number)):
            if number[i] == '.':
                int_side = number[:i]
                dec_side = number[i + 1:]
                break
        while not (int_side.isdigit()) or not (dec_side.isdigit()) and dec_side != '':
            dec_side = ''
            # print('Only numbers are allowed! (decimals included, but not fractions)')
            int_side = number
            for i in range(0, len(number)):
                if number[i] == '.':
                    int_side = number[:i]
                    dec_side = number[i + 1:]
            user_choice = input()
        int_length = len(int_side)
        ones = ['', 'one ', 'two ', 'three ', 'four ', 'five ', 'six ', 'seven ', 'eight ', 'nine ']
        teens = ['ten ', 'eleven ', 'twelve ', 'thirteen ', 'fourteen ', 'fifteen ', 'sixteen ', 'seventeen ',
                 'eighteen ',
                 'nineteen ']
        decades = ['', '', 'twenty ', 'thirty ', 'forty ', 'fifty ', 'sixty ', 'seventy ', 'eighty ', 'ninety ']
        hundreds = ['', 'one hundred ', 'two hundred ', 'three hundred ', 'four hundred ', 'five hundred ',
                    'six hundred ',
                    'seven hundred ', 'eight hundred ', 'nine hundred ']
        comma = ['thousand ', 'million ', 'trillion ', 'quadrillion ']
        word = ''
        int_length = len(int_side)
        dec_length = len(dec_side)
        change = int_length
        up_change = 0
        while change > 0:
            if int_side == '':
                break
            if number == '0':
                word = 'zero'
                break
            elif change > 1 and int_side[change - 2] == '1':
                for i in range(0, 10):
                    if int_side[change - 1] == str(i):
                        word = teens[i] + word
            else:
                if change > 0:
                    for i in range(0, 10):
                        if int_side[change - 1] == str(i):
                            word = ones[i] + word
                if change > 1:
                    for i in range(0, 10):
                        if int_side[change - 2] == str(i):
                            word = decades[i] + word
            if change > 2:
                for i in range(0, 10):
                    if int_side[change - 3] == str(i):
                        word = hundreds[i] + word
            if change > 3:
                word = comma[up_change] + word
            change -= 3
            up_change += 1
        # if dec_side == '':
        # word += ' birr '

        print(dec_side)
        """
        for i in range(0, len(dec_side)):
            for x in range(0, 10):
                if dec_side[i] == str(x):
                    word += ones[x]"""

        if dec_side not in ['', '0', '00']:
            word += ' birr and '
            word += self.convert_to_cents(dec_side) + " cents only"
        else:
            word += ' birr only'

        # word += " only"

        return word.title()

    def convert_to_cents(self, number):
        number = str(number)
        int_side = number
        dec_side = ''
        for i in range(0, len(number)):
            if number[i] == '.':
                int_side = number[:i]
                dec_side = number[i + 1:]
                break
        while not (int_side.isdigit()) or not (dec_side.isdigit()) and dec_side != '':
            dec_side = ''
            # print('Only numbers are allowed! (decimals included, but not fractions)')
            int_side = number
            for i in range(0, len(number)):
                if number[i] == '.':
                    int_side = number[:i]
                    dec_side = number[i + 1:]
            user_choice = input()
        int_length = len(int_side)
        ones = ['', 'one ', 'two ', 'three ', 'four ', 'five ', 'six ', 'seven ', 'eight ', 'nine ']
        teens = ['ten ', 'eleven ', 'twelve ', 'thirteen ', 'fourteen ', 'fifteen ', 'sixteen ', 'seventeen ',
                 'eighteen ',
                 'nineteen ']
        decades = ['', '', 'twenty ', 'thirty ', 'forty ', 'fifty ', 'sixty ', 'seventy ', 'eighty ', 'ninety ']
        hundreds = ['', 'one hundred ', 'two hundred ', 'three hundred ', 'four hundred ', 'five hundred ',
                    'six hundred ',
                    'seven hundred ', 'eight hundred ', 'nine hundred ']
        comma = ['thousand ', 'million ', 'trillion ', 'quadrillion ']
        word = ''
        int_length = len(int_side)
        dec_length = len(dec_side)
        change = int_length
        up_change = 0
        while change > 0:
            if int_side == '':
                break
            if number == '0':
                word = 'zero'
                break
            elif change > 1 and int_side[change - 2] == '1':
                for i in range(0, 10):
                    if int_side[change - 1] == str(i):
                        word = teens[i] + word
            else:
                if change > 0:
                    for i in range(0, 10):
                        if int_side[change - 1] == str(i):
                            word = ones[i] + word
                if change > 1:
                    for i in range(0, 10):
                        if int_side[change - 2] == str(i):
                            word = decades[i] + word
            if change > 2:
                for i in range(0, 10):
                    if int_side[change - 3] == str(i):
                        word = hundreds[i] + word
            if change > 3:
                word = comma[up_change] + word
            change -= 3
            up_change += 1

        return word.title()

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
