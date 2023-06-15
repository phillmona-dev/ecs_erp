import json
import os.path
import xml.dom.minidom
import xml.etree.cElementTree as ET
from datetime import datetime
import requests
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from io import BytesIO


try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes

class account_move(models.Model):
    _inherit = "account.move"

    logged_user_id = fields.Many2one('res.users')
    current_user_id = fields.Many2one('res.users', compute="_get_current_user_id")
    # = fields.Many2one('res.users', string='My User', default=lambda self: self.env.user)

    FPMachineID = fields.Char("Machine ID")
    FSInvoiceNumber = fields.Char("FS Invoice Number")
    EJNumber = fields.Char("EJ Number")
    FTimeStamp = fields.Datetime("TimeStamp")
    is_invoice_printed_pos = fields.Boolean("Invoice Printed POS", default=False)
    tin_no = fields.Char(compute="get_tin_no", string="Tin No")
    sales_type = fields.Char('Sales order type', compute='_get_so_type', store=True)
    order_from = fields.Char("Order From", compute='_compute_order_from')

    customer_name1 = fields.Char(compute='_compute_order_from', string='Customer Name')
    cust_id = fields.Char(compute='_compute_order_from', string='Customer Name')

    pos_device_ip_address = fields.Char("POS IP Address", compute='get_pos_address')
    pos_xml_folder = fields.Char("XML Folder Path", compute='get_pos_address')
    total_amount_word = fields.Char(compute="_get_total_amount_word")

    fileout = fields.Binary('File', readonly=True)
    core_amt = fields.Float('Core amount', compute="_get_core_amt",store=True)
    non_core_amt = fields.Float('Non-core amount', compute="_get_core_amt",store=True)

    @api.depends ('invoice_line_ids.price_subtotal')
    def _get_core_amt(self):

        for rec in self:
            core_sum = 0;
            for records in rec.invoice_line_ids:
                if records.product_id.product_tmpl_id.is_core_product:
                    core_sum = core_sum + records.price_subtotal
            rec.core_amt = core_sum
            rec.non_core_amt = rec.amount_total_in_currency_signed - core_sum

    def _compute_order_from(self):
        for record in self:
            recs = self.env['sale.order'].search([('name', '=', record.invoice_origin)])
            record.customer_name1 = ''
            record.cust_id = ''
            for r in recs:
                # get customer name
                record.cust_id = r.cust_id
                record.customer_name1 = r.cust_name
                if r.order_type:
                    record.order_from = r.order_type
                else:
                    record.order_from = r.order_from

    def _get_current_user_id(self):
        context = self._context
        self.current_user_id = self.env.user
        # return context.get('uid')

    def _get_total_amount_word(self):
        for record in self:
            # convert amount to word
            amount_in_word = self.convert_to_word(record.amount_total)
            last_word = self.lastWord(amount_in_word)
            if last_word == 'Cents':
                record.total_amount_word = amount_in_word + " Only"
            else:
                record.total_amount_word = amount_in_word + " Birr Only"

    # @api.depends("partner_id")
    def get_tin_no(self):
        for record in self:
            record.tin_no = record.partner_id.vat

    @api.depends('invoice_payment_term_id')
    def _get_so_type(self):
        for rec in self:
            if rec.invoice_payment_term_id.apply_credit_limit:
                rec.sales_type = 'Credit'
            elif rec.invoice_payment_term_id.name == 'Sales return':
                rec.sales_type = 'Sales return'
            else:
                rec.sales_type = 'Cash'

    def get_pos_address(self):
        employee_rec = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)

        # set pos ip address
        self.pos_device_ip_address = employee_rec.pos_device_ip_address
        self.pos_xml_folder = employee_rec.pos_xml_folder

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        return super().get_view(view_id, view_type, **options)

    def view_init(self):
        pass

    def generate_sales_xml(self):

        file_io = BytesIO()
        # get employee record

        if not self.pos_xml_folder:
            raise ValidationError(
                "The POS device IP address is not set for the current user, please contact the system administrator to set it.")

        for record in self:
            m_encoding = 'UTF-8'

            # Get Payment Type
            payment_type = record.sales_type

            Invoice = ET.Element("Invoice")
            # doc = ET.SubElement(Invoice, "status", date="20210123")
            ET.SubElement(Invoice, "Invoice_Type").text = "Invoice"
            ET.SubElement(Invoice, "Reference_Number").text = record.name
            ET.SubElement(Invoice, "Invoice_Date").text = str(
                record.invoice_date.month) + "." + str(record.invoice_date.day) + "." + str(record.invoice_date.year)
            ET.SubElement(Invoice, "Customer_Code").text = str(record.partner_id.id)
            ET.SubElement(
                Invoice, "Customer_Name").text = record.partner_id.name
            ET.SubElement(Invoice, "Customer_TIN").text = record.partner_id.vat
            ET.SubElement(Invoice, "Payment_Type").text = payment_type
            ET.SubElement(Invoice, "Invoice_DiscOrAdd_Amount").text = "0.00"

            for line in record.invoice_line_ids:

                tax_percent = 0
                # get tax id
                for tax_id in line.tax_ids:
                    if tax_id.type_tax_use == "sale" and tax_id.real_amount == 15:
                        tax_percent = 15

                Line_Items = ET.SubElement(Invoice, "Line_Items")
                ET.SubElement(Line_Items, "Item_ID").text = line.product_id.default_code
                ET.SubElement(Line_Items, "Item_Description").text = line.product_id.name
                ET.SubElement(Line_Items, "Item_Quantity").text = str(line.quantity)
                ET.SubElement(Line_Items, "Item_UOM").text = str(line.product_uom_id.name)
                ET.SubElement(Line_Items, "Item_Unit_Price").text = str(line.price_unit)
                ET.SubElement(Line_Items, "Item_Tax_Percent").text = str(tax_percent)
                ET.SubElement(Line_Items, "Item_DiscOrAdd_Amount").text = "0.00"

            dom = xml.dom.minidom.parseString(ET.tostring(Invoice))
            xml_string = dom.toprettyxml()
            part1, part2 = xml_string.split('?>')

            self.fileout = encodebytes(xml_string.encode('utf-8'))

            # save path
            save_path = record.pos_xml_folder
            name_of_file = record.name
            completeName = os.path.join(save_path, name_of_file + ".xml")


            ##with open(completeName, 'w') as xfile:
                ##xfile.write(
                    ##part1 + 'encoding=\"{}\"?>\n'.format(m_encoding) + part2)
                ##xfile.close()


            # change text into a binary array

            # This downloads file. The file is fileout and the name if filename
            return {
                    'type': 'ir.actions.act_url',
                    'target': 'new',
                    'url': 'web/content/?model=' + self._name + '&id=' + str(
                        self.id) + '&field=fileout&download=true&filename=' + name_of_file+".xml",
            }

    def print_to_pos_peds(self):

        context = self._context

        for record in self:

            # Get Payment Type
            payment_type = "Credit"

            if record.invoice_payment_term_id.deliv_after_payment:
                payment_type = "Credit"

            header = {
                "ThirdPartyID": "Odoo",
                "TenantId": "TenantId",
                "TransactionID": str(record.id),
                "ReferenceNumber": record.invoice_origin,
                "PaymentType": payment_type,
                "PaymentReferenceNumber": record.name,
                "BuyerName": record.partner_id.name,
                "BuyerTaxIdNumber": record.partner_id.vat,
                "AddOnType": "percentage",
                "AddOnValue": "0",
                "DiscountType": "fixed",
                "DiscountValue": "0",
                "UserName": str(self.logged_user_id.name),
                "HeaderMemo": "Free Text",
                "FooterMemo": "Welcome Message",
                "TimeStamp": str(datetime.now().strftime("%Y-%m-%d %I:%M:%S")),
                "Remark": "",
                "ApprovedBy": str(self.logged_user_id.name),
                "LineItem": [

                ]

            }

            for line in record.invoice_line_ids:
                line_id = 1

                tax_percent = 0
                # get tax id
                for tax_id in line.tax_ids:
                    if tax_id.type_tax_use == "sale":  # and tax_id.real_amount == 15:
                        tax_percent = tax_id.real_amount

                line_item = {
                    "LineIndex": str(line_id),
                    "ItemTransactionId": str(line.id),
                    "ItemID": str(line.product_id.default_code),
                    "ItemShortName": str(line.product_id.name),
                    "ItemDescription": str(line.product_id.name),
                    "UnitName": str(line.product_uom_id.name),
                    "Quantity": str('%.2f' % line.quantity),
                    "UnitPrice": str('%.2f' % line.price_unit),
                    "TaxRate": str('%.2f' % tax_percent),
                    "AddOnType": "percentage",
                    "AddOnValue": "0",
                    "DiscountType": "fixed",
                    "DiscountValue": "0"
                }
                header["LineItem"].append(line_item)
                line_id += 1

        json_string = json.dumps(header)

        headers = {'ApiKey': 'b904ea3c8a3446a0894aeec285e774b7', 'Content-Type': 'application/json'}
        request = requests.post('http://192.168.10.64:8545/pedsfpsrv/api/SalesInvoice/PrintInvoice?printCopy=false',
                                data=json_string, headers=headers)

        return True

    def print_sales_attachment(self):
        if self.order_from in ('IM', 'WS', 'IM-IM', 'IM-WS'):
            res1 = self.env.ref('droga_sales.droga_sales_pos_attachment_action').report_action(self)
        else:
            res1 = self.env.ref('droga_sales.droga_sales_pos_attachment_a5_action').report_action(self)
        return res1

    def convert_to_word(self, number):
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
            #user_choice = input()
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
            word += self.convert_to_word(dec_side) + " cents"

        # word += " only"

        return word.title()

    # Function which returns last word
    def lastWord(self, string):
        # taking empty string
        newstring = ""
        # calculating length of string
        length = len(string)
        # traversing from last
        for i in range(length - 1, 0, -1):
            # if space is occurred then return
            if (string[i] == " "):
                # return reverse of newstring
                return newstring[::-1]
            else:
                newstring = newstring + string[i]

    def set_analytic_accounts(self):
        # get analytic account
        analytic_distribution = ""
        tax_ids = ''
        for record in self.invoice_line_ids:
            if record.analytic_distribution:
                analytic_distribution = record.analytic_distribution
            if record.tax_ids:
                tax_ids = record.tax_ids

            if analytic_distribution != '' and tax_ids != '':
                break

        if analytic_distribution == '' and tax_ids == '':
            ValidationError("At least fill the first line!")

        # fill empty analytic lines
        for record in self.invoice_line_ids:
            if analytic_distribution != '':
                record.analytic_distribution = analytic_distribution
            if tax_ids != '':
                record.tax_ids = tax_ids


class account_move_line(models.Model):
    _inherit = "account.move.line"

    @api.depends("product_id")
    def get_item_code(self):
        for record in self:
            record.item_code = record.product_id.product_tmpl_id.default_code

    item_code = fields.Char(compute="get_item_code", string="Item Code", store=True)
    item_description_alternate = fields.Char("Item Description Alternate")
    item_uom_alternate = fields.Char("UoM Alternate", default="")

    @api.onchange('analytic_distribution')
    def analytic_distribution(self):
        ValidationError("Hello")
