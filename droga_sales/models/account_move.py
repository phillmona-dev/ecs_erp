from odoo import _, api, fields, models
import xml.etree.cElementTree as ET
import xml.dom.minidom
import os.path
import json
from datetime import datetime
import requests
from json import JSONEncoder

from odoo.exceptions import UserError


class MyEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


class account_move(models.Model):
    _inherit = "account.move"

    def get_current_user_id(self):
        context = self._context
        return context.get('uid')

    logged_user_id = fields.Many2one('res.users', default=get_current_user_id)

    FPMachineID = fields.Char("FPMachineID")
    FSInvoiceNumber = fields.Char("FSInvoiceNumber")
    EJNumber = fields.Char("EJNumber")
    FTimeStamp = fields.Datetime("FTimeStamp")

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
                    if tax_id.type_tax_use == "sale":# and tax_id.real_amount == 15:
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



        headers = {'ApiKey': 'b904ea3c8a3446a0894aeec285e774b7','Content-Type': 'application/json'}
        request = requests.post('http://192.168.10.64:8545/pedsfpsrv/api/SalesInvoice/PrintInvoice?printCopy=false',
                                data=json_string, headers=headers)


        return True
