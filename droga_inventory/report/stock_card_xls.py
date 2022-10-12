import base64
import io

from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import datetime

try:
    from base64 import encodebytes
except ImportError:
    from base64 import encodestring as encodebytes

#class tender_master_xls(models.AbstractModel):     Default type
#My point is to have a transient model inherit the report.report_xlsx.abstract and immplement all logic and use interface from here as well
class tender_master_xls(models.TransientModel):
    _name='droga.inventory.reports.excel'
    #_inherit = 'report.report_xlsx.abstract'

    warehouse=fields.Many2one('stock.warehouse','Warehouse')
    product = fields.Many2one('product.product','Product')
    date_from=fields.Date('Date from')
    date_to = fields.Date('Date to')
    fileout = fields.Binary('File', readonly=True)
    #fileout_filename = fields.Char('Filename', readonly=True)

    def action_get_xls(self):
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
        filename = '%s_%s_%s' % ('Stock card',self.warehouse.name, datetime_string)
        filename += '%2Exlsx'

        #This downloads file. The file is fileout and the name if filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=fileout&download=true&filename=' + filename,
        }

    def generate_xlsx_report(self, workbook):
        sheet = workbook.add_worksheet('StockCard')
        self.get_droga_stockcard_sheet_with_header(sheet,workbook,0)
        self.get_droga_stockcard_sheet_with_header(sheet, workbook, 15)


    def get_droga_stockcard_sheet_with_header(self, sheet,workbook,row_start):

        sheet.set_column('B:B', 10)
        #region excel_formats
        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 22})
        main_title_format = workbook.add_format({
            'bold': 0,
            'border': 1,
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
            'text_wrap':1,
            'fg_color': '#F6F5F5'})
        #endregion


        #sheet.insert_image(row_start,8,"logo.png",{'image_data':droga_logo})

        #Sets row height to 30
        sheet.set_row(row_start, 30)
        sheet.set_row(row_start+1, 30)

        sheet.merge_range('A'+str(row_start+1)+':L'+str(row_start+1), 'DROGA PHARMA PLC', header_format)
        sheet.merge_range('A'+str(row_start+2)+':L'+str(row_start+2), 'Stock record card', main_title_format)
        sheet.merge_range('A'+str(row_start+3)+':L'+str(row_start+3), 'Product name, strength and dosage form : ', parameter_format)

        sheet.merge_range('A'+str(row_start+4)+':F'+str(row_start+4), 'Unit of measure : ', parameter_format)
        sheet.merge_range('G'+str(row_start+4)+':L'+str(row_start+4), 'Location : ', parameter_format)

        sheet.merge_range('A'+str(row_start+5)+':F'+str(row_start+5), 'Maximum stock level : ', parameter_format)
        sheet.merge_range('G'+str(row_start+5)+':L'+str(row_start+5), 'Emergency order point : ', parameter_format)

        sheet.merge_range('A'+str(row_start+6)+':F'+str(row_start+6), 'Average monthly consumption (AMC) : ', parameter_format)
        sheet.merge_range('G'+str(row_start+6)+':L'+str(row_start+6), 'Product category : ', parameter_format)

        sheet.merge_range('A'+str(row_start+7)+':L'+str(row_start+7), '', separator_format)

        sheet.merge_range('A'+str(row_start+8)+':A'+str(row_start+10), 'Date', title_format)
        sheet.merge_range('B'+str(row_start+8)+':B'+str(row_start+10), 'Doc No.\n(Receiving\nor Issue)', title_format)
        sheet.merge_range('C'+str(row_start+8)+':C'+str(row_start+10), 'Received\nfrom or\nIssued to)', title_format)

        sheet.merge_range('D'+str(row_start+8)+':G'+str(row_start+9), 'Quantity', title_format)
        sheet.write(row_start+9, 3, 'Received',title_format)
        sheet.write(row_start+9, 4, 'Issued', title_format)
        sheet.write(row_start+9, 5, 'Loss/Adj.', title_format)
        sheet.write(row_start+9, 6, 'Balance', title_format)

        sheet.merge_range('H'+str(row_start+8)+':I'+str(row_start+9), 'Unit Price', title_format)
        sheet.write(row_start+9, 7, 'Birr', title_format)
        sheet.write(row_start+9, 8, 'Cent', title_format)

        sheet.merge_range('J'+str(row_start+8)+':J'+str(row_start+10), 'Batch #', title_format)
        sheet.merge_range('K'+str(row_start+8)+':K'+str(row_start+10), 'Expiry\nDate', title_format)
        sheet.merge_range('L'+str(row_start+8)+':L'+str(row_start+10), 'Remark', title_format)
        return sheet

