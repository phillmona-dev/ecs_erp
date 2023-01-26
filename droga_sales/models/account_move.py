import json
import os.path
import xml.dom.minidom
import xml.etree.cElementTree as ET
from datetime import datetime
import requests
from odoo import api, fields, models


class account_move(models.Model):
    _inherit = "account.move"

    def get_current_user_id(self):
        context = self._context
        return context.get('uid')

    logged_user_id = fields.Many2one('res.users', default=get_current_user_id)

    FPMachineID = fields.Char("Machine ID")
    FSInvoiceNumber = fields.Char("FS Invoice Number")
    EJNumber = fields.Char("EJ Number")
    FTimeStamp = fields.Datetime("TimeStamp")
    is_invoice_printed_pos = fields.Boolean("Invoice Printed POS", default=False)
    tin_no = fields.Char(compute="get_tin_no", string="Tin No", store=True)
    sales_type = fields.Char('Sales order type', compute='_get_so_type', store=True)

    pos_device_ip_address = fields.Char("POS IP Address", compute='get_pos_address')
    total_amount_word = fields.Char(compute="_get_total_amount_word")

    def _get_total_amount_word(self):
        for record in self:
            # convert amount to word
            record.total_amount_word = self.convert_to_word(record.amount_total)

    @api.depends("partner_id")
    def get_tin_no(self):
        for record in self:
            record.tin_no = record.partner_id.vat
            # convert amount to word
            record.amount_total_word = self.convert_to_word(record.amount_total)

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

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        return super().get_view(view_id, view_type, **options)

    def view_init(self):
        pass

    def generate_sales_xml(self):

        for record in self:
            m_encoding = 'UTF-8'

            # Get Payment Type
            payment_type = "Cash"

            if record.invoice_payment_term_id.deliv_after_payment:
                payment_type = "Credit"

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

            # save path
            save_path = 'C:/xml/'
            name_of_file = record.name
            completeName = os.path.join(save_path, name_of_file + ".xml")

            with open(completeName, 'w') as xfile:
                xfile.write(
                    part1 + 'encoding=\"{}\"?>\n'.format(m_encoding) + part2)
                xfile.close()

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
        res1 = self.env.ref('droga_sales.droga_sales_pos_attachment_action').report_action(self)
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
        # word += 'birr '

        print(dec_side)
        """
        for i in range(0, len(dec_side)):
            for x in range(0, 10):
                if dec_side[i] == str(x):
                    word += ones[x]"""

        if dec_side not in ['', '0', '00']:
            word += 'birr and '
            word += self.convert_to_word(dec_side) + " cents"

        word += " only"

        return word.title()


class account_move_line(models.Model):
    _inherit = "account.move.line"

    @api.depends("product_id")
    def get_item_code(self):
        for record in self:
            record.item_code = record.product_id.product_tmpl_id.default_code

    item_code = fields.Char(compute="get_item_code", string="Item Code", store=True)
