from odoo import _, api, fields, models
import xml.etree.cElementTree as ET
import xml.dom.minidom
import os.path


class account_move(models.Model):
    _inherit = "account.move"

    def generate_sales_xml(self):

        for record in self:
            m_encoding = 'UTF-8'

            Invoice = ET.Element("Invoice")
            #doc = ET.SubElement(Invoice, "status", date="20210123")
            ET.SubElement(Invoice, "Invoice_Type").text = "Invoice"
            ET.SubElement(Invoice, "Reference_Number").text = record.name
            ET.SubElement(Invoice, "Invoice_Date").text = str(
                record.invoice_date.month)+"."+str(record.invoice_date.day)+"."+str(record.invoice_date.year)
            ET.SubElement(Invoice, "Customer_Code").text = str(record.partner_id.id)
            ET.SubElement(
                Invoice, "Customer_Name").text = record.partner_id.name
            ET.SubElement(Invoice, "Customer_TIN").text = record.partner_id.vat
            ET.SubElement(Invoice, "Payment_Type").text = "Cash"
            ET.SubElement(Invoice, "Invoice_DiscOrAdd_Amount").text = "0.00"

            for line in record.invoice_line_ids:
                Line_Items = ET.SubElement(Invoice, "Line_Items")
                ET.SubElement(Line_Items, "Item_ID").text = line.product_id.default_code
                ET.SubElement(Line_Items, "Item_Description").text = line.product_id.name
                ET.SubElement(Line_Items, "Item_Quantity").text = str(line.quantity)
                ET.SubElement(Line_Items, "Item_UOM").text = str(line.product_uom_id.name)
                ET.SubElement(Line_Items, "Item_Unit_Price").text = str(line.price_unit)
                ET.SubElement(Line_Items, "Item_Tax_Percent").text =str(line.tax_ids[0].amount) if line.tax_ids else "0.00"
                ET.SubElement(Line_Items, "Item_DiscOrAdd_Amount").text = "0.00"

            dom = xml.dom.minidom.parseString(ET.tostring(Invoice))
            xml_string = dom.toprettyxml()
            part1, part2 = xml_string.split('?>')

            # save path
            save_path = 'C:/xml/'
            name_of_file = record.name
            completeName = os.path.join(save_path, name_of_file+".xml")

            with open(completeName, 'w') as xfile:
                xfile.write(
                    part1 + 'encoding=\"{}\"?>\n'.format(m_encoding) + part2)
                xfile.close()
