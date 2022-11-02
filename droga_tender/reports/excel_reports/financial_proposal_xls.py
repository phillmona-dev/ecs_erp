from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import datetime
from odoo.exceptions import UserError

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes

#class tender_master_xls(models.AbstractModel):     Default type
#My point is to have a transient model inherit the report.report_xlsx.abstract and immplement all logic and use interface from here as well
class tender_financial_proposal_master_xls(models.TransientModel):
    _name='droga.tender.reports.financial.proposal'

    tender_id=fields.Many2one('droga.tender.master','Tender')

    fileout = fields.Binary('File', readonly=True)
    #fileout_filename = fields.Char('Filename', readonly=True)

    def action_get_xls(self):
        if not self.tender_id:
            raise UserError("Tender must be selected.")

        #This generates our excel file
        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)
        self.generate_xlsx_report(workbook)
        workbook.close()

        #The file to download will be stored under fileout field
        self.fileout = encodebytes(file_io.getvalue())
        file_io.close()

        #The file name is stored under filename
        datetime_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = '%s_%s_%s' % ('Financial proposal ',self.tender_id['ten_name'], datetime_string)
        filename += '%2Exlsx'

        #This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def generate_xlsx_report(self, workbook):
        sheet = workbook.add_worksheet('Financial proposal')

        sheet.set_column('A:A', 10.5)
        sheet.set_column('B:B', 35)
        sheet.set_column('C:C', 11)
        sheet.set_column('D:D', 14)
        sheet.set_column('E:E', 18)
        sheet.set_column('F:F', 18)
        sheet.set_column('G:G', 16)
        row_start=0
        date_format = workbook.add_format({'num_format': 'd mmm yyyy', 'border': 7})
        num_format = workbook.add_format({'num_format': 43, 'border': 7})
        cent_format = workbook.add_format({'num_format': 41, 'border': 7})
        border = workbook.add_format({'border': 7})
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 22})
        main_title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16})
        parameter_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#F6F5F5'})

        separator_format = workbook.add_format({
            'bold': 1,
            'border': 7,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#D9D9D9'})

        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        title_format_num= workbook.add_format({
            'bold': 1,
            'border': 1,
            'num_format': 43,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})

        sheet.merge_range('A' + str(row_start + 1) + ':G' + str(row_start + 1), self.tender_id['customer'].name, header_format)
        sheet.merge_range('A' + str(row_start + 2) + ':G' + str(row_start + 2), self.tender_id['procurement_title'],header_format)
        sheet.merge_range('A' + str(row_start + 3) + ':G' + str(row_start + 3), 'Financial proposal',main_title_format)

        sheet.write(row_start+4, 0, 'S.No',title_format)
        sheet.write(row_start + 4, 1, 'Items', title_format)
        sheet.write(row_start + 4, 2, 'Unit', title_format)
        sheet.write(row_start + 4, 3, 'Qty', title_format)
        sheet.write(row_start + 4, 4, 'Unit price', title_format)
        sheet.write(row_start + 4, 5, 'Total price', title_format)
        sheet.write(row_start + 4, 6, 'Remark', title_format)
        row_start=5

        tot_amount=0

        for rec in self.tender_id['detail_submissions_fin']:
            sheet.write(row_start, 0, rec.item_num,border)
            item=rec.item_pro if rec.item_pro else rec.type_item.type_or_item_name
            sheet.write(row_start, 1, item if item else ' ',border)
            uom=rec.uom_free_field if rec.uom_free_field else rec.unit_of_measure
            sheet.write(row_start, 2, uom if uom else ' ',border)
            sheet.write(row_start, 3, rec.quantity,num_format)
            sheet.write(row_start, 4, rec.unit_price,num_format)
            sheet.write(row_start, 5, rec.amount,num_format)
            tot_amount+=rec.amount
            sheet.write(row_start, 6, rec.remark if rec.remark else ' ',border)

            row_start+=1

        sheet.write(row_start , 4, 'Total price', title_format)
        sheet.write(row_start, 5, tot_amount, title_format_num)

        row_start+=2

        sheet.write(row_start, 1, 'The Price is Valid for a period of 60 days.')
        sheet.write(row_start+1, 1, 'The Price include all the cost to the purchaser store.')
        sheet.write(row_start + 2, 1, 'Terms of Payment: Cash up on delivery or as per  the purchaser payment policy.')
        sheet.write(row_start + 3, 1, 'Delivery time: with in 3-5  days.')
        sheet.write(row_start + 5, 1, 'Prepared by: __________________________')
        sheet.write(row_start + 5, 4, 'Approved by: __________________________')