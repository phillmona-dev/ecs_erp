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
class droga_account_loan_reports_xls(models.TransientModel):
    _name='droga.account.loan.reports.xls'
    

    loan_id=fields.Many2one('account.loan','Loan')


    fileout = fields.Binary('File', readonly=True)
    #fileout_filename = fields.Char('Filename', readonly=True)

    def action_get_xls(self):
        if not self.loan_id:
            raise UserError("Loan must be selected.")

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
        filename = '%s_%s_%s' % ('Loan Amortization ',self.loan_id['name'].id, datetime_string)
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
        # current_date=datetime.today()
        # cday = current_date.date()
        sday=self.loan_id.interest_start_date
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
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 18})
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

        sheet.merge_range('A' + str(row_start + 1) + ':O' + str(row_start + 1), self.loan_id.company_id.id, header_format)
        sheet.merge_range('A' + str(row_start + 2) + ':O' + str(row_start + 2), "LOAN AMORTIZATION", header_format)
        sheet.merge_range('K' + str(row_start + 3) + ':L' + str(row_start + 3), "BANK", )
        sheet.merge_range('M' + str(row_start + 3) + ':M' + str(row_start + 3), self.loan_id['name'].name, )
        contractdate= self.loan_id['contract_date'].strftime("%Y/%m/%d")
        sheet.merge_range('K' + str(row_start + 4) + ':L' + str(row_start + 4), "Loan Type", )
        sheet.merge_range('M' + str(row_start + 4) + ':M' + str(row_start + 4), self.loan_id['loan_type'].name, )
        sheet.merge_range('K' + str(row_start + 5) + ':L' + str(row_start + 5), "Statment Number", )
        sheet.merge_range('M' + str(row_start + 5) + ':M' + str(row_start + 5), self.loan_id['loan_statement_number'], )
        sheet.write(row_start+2, 12, self.loan_id['name'].name,)
        sheet.write(row_start + 3, 12, self.loan_id['loan_type'].name)
        sheet.write(row_start + 4, 12, self.loan_id['loan_statement_number'])
        #sheet.write(row_start + 5, 13, contractdate)#
        sheet.merge_range('K' + str(row_start + 7) + ':L' + str(row_start + 7), "Schedule Payment", )
        sheet.merge_range('K' + str(row_start + 8) + ':L' + str(row_start + 8), "Schedule Number of Payments", )
        sheet.merge_range('K' + str(row_start + 9) + ':L' + str(row_start + 9), "Grace Period", )
        sheet.merge_range('K' + str(row_start + 10) + ':L' + str(row_start + 10), "Total Interest", )
        sheet.merge_range('K' + str(row_start + 11) + ':L' + str(row_start + 11), "Contract Date", )
        sheet.write(row_start + 6, 12, self.loan_id.payment)
        sheet.write(row_start + 7, 12, self.loan_id.schedule_numberof_payment)
        sheet.write(row_start + 8, 12, '')
        sheet.write(row_start + 9, 12, self.loan_id.total_interest+self.loan_id.total_penality)
        sheet.write(row_start + 10, 12, contractdate)
        
        
        
        
        sheet.merge_range('A' + str(row_start + 7) + ':C' + str(row_start + 7), "Loan Amount",)
        sheet.merge_range('A' + str(row_start +8) + ':C' + str(row_start + 8), "Anual Interest Rate",)
        sheet.merge_range('A' + str(row_start + 9) + ':C' + str(row_start + 9), "Loan Period In Years",)
        sheet.merge_range('A' + str(row_start + 10) + ':C' + str(row_start + 10), "Number Of Payment per Yeart",)
        sheet.merge_range('A' + str(row_start + 11) + ':C' + str(row_start + 11), "Daily Interest Rate",)
        sheet.write(row_start + 6,3, self.loan_id.loan_amount)
        sheet.write(row_start + 7,3, self.loan_id.anual_interest_rate)
        sheet.write(row_start + 8, 3, self.loan_id.loan_period_year)
        sheet.write(row_start + 9, 3, self.loan_id.total_number_of_payment)
        sheet.write(row_start + 10, 3, self.loan_id.daily_interest_rate)
        
      
        #sheet.merge_range('A' + str(row_start + 11) + ':C' + str(row_start + 7), "Contract Date",)
        
        sheet.merge_range('A' + str(row_start + 3) + ':G' + str(row_start + 3), 'Loan Amount',main_title_format)
        
        sheet.write(row_start+12, 0, 'Year',title_format)
        sheet.write(row_start + 12, 1, 'Month', title_format)
        sheet.write(row_start + 12, 2, 'Value Date', title_format)
        sheet.write(row_start + 12, 3, 'Description', title_format)
        sheet.write(row_start + 12, 4, 'Receipt', title_format)
        sheet.write(row_start + 12, 5, 'Repayment', title_format)
        sheet.write(row_start + 12, 6, 'Cumulative Balance', title_format)
        sheet.write(row_start + 12, 7, 'Interest on Unpaied Princpal', title_format)
        sheet.write(row_start + 12, 8, 'Penalty Interest', title_format)
        sheet.write(row_start + 12, 9, 'Penalty Payment', title_format)
        sheet.write(row_start + 12, 10, 'Repayment', title_format)
        sheet.write(row_start + 12, 11, 'Cumulative Balance', title_format)
        sheet.write(row_start + 12, 12, 'Total Outstanding Balance', title_format)
        sheet.merge_range('D' + str(row_start + 12) + ':G' + str(row_start + 12), "Principal",title_format)
        sheet.merge_range('H' + str(row_start + 12) + ':L' + str(row_start + 12), "Interest",title_format)
        row_start=13
        daily_loan = self.env['droga.loan.daily.report'].search(
            [('id', 'in', self.loan_id.ids)])
        balance=0
        recipt=0
        inte=0.000
        penality=0
        ipayment=0
        ppayment=0
        pealitypay=0
        cinterest=0
        daily_loan = self.env['droga.loan.daily.report'].search(
            [('acount_loan_id', '=', self.loan_id.id), ],order='value_date')
        datee=self.loan_id.contract_date

        for daily in daily_loan:
            if datee!=daily.value_date:
                datee=daily.value_date
                sheet.write(row_start, 0, daily['value_date'].year,border)
                sheet.write(row_start, 1, daily['value_date'].month,border)
                sheet.write(row_start, 2, daily['value_date'].strftime("%Y/%m/%d"),border)
                # sheet.write(row_start, 2, 'ABCD',border)
                sheet.write(row_start, 3,  ' ')
                inte+= daily['daily_interest_amount']
                penality+=daily['daily_penality_amount']
               
            
                sheet.write(row_start, 7, daily['daily_interest_amount'],border)
                daily_reciept= self.env['droga.loan.daily.report'].search(
            [('acount_loan_id', '=', self.loan_id.id),('date','=',daily.value_date) ],order='value_date')
                
                for recie in daily_reciept :
                        if recie['date']==daily['value_date']:
                            recipt+= recie['receipt']
                            sheet.write(row_start, 4, recie['receipt'],border)
                            break
                        else:
                            sheet.write(row_start, 4, ' ',border)
                # daily_repay= self.env['droga.loan.daily.report'].search(
                #      [('acount_loan_id', '=', self.loan_id.id),('pdate','=',daily.value_date) ],order='value_date')
                daily_repay= self.env['droga.loan.daily.report'].search(
                    [('acount_loan_id', '=', self.loan_id.id),('pdate','=',daily.value_date) ],order='value_date')
               
                for repay in daily_repay:
                        if repay['pdate']==daily['value_date'] :
                           ppayment+= repay.principal_repayment
                           ipayment+=repay.interst_payment


                           sheet.write(row_start, 5,repay.principal_repayment,border)
                           sheet.write(row_start, 9,repay.is_penality,border)
                           sheet.write(row_start, 10,repay.interst_payment,border)
                           pealitypay+=repay.is_penality
                           break
                cumu=recipt-ppayment
                sheet.write(row_start, 6,recipt-ppayment, )
                cinterest=penality+inte- ipayment-pealitypay
                sheet.write(row_start, 11, cinterest, )
                sheet.write(row_start, 12, cinterest+cumu, )
                
        # for dailyy in self.loan_id.loan_interest_ids.sorted(key=lambda r: r.value_date):
        #     sheet.write(row_start, 0, dailyy['value_date'].year, )
        #     #item=rec.item_pro if rec.item_pro else rec.type_item.type_or_item_name
        #     sheet.write(row_start, 1, dailyy['value_date'].month, )
        #     sheet.write(row_start, 2, dailyy['value_date'].strftime("%Y/%m/%d"), )
            
            
        #     sheet.write(row_start, 3,  ' ')
        #     a=0
        #     daily_loan = self.env['droga.loan.daily.report'].search(
        #     [('id', '=', self.loan_id.id),])
        #     for daily in daily_loan:
        #         # if a==0 :
        #         #     if daily['value_date']:
        #         #         if daily['value_date']==dailyy['value_date'] :
        #                     #sheet.write(row_start, 4, daily['receipt'], )
        #         inte+= daily['daily_interest_amount']
        #         penality+=daily['daily_penality_amount']
                            
        #         sheet.write(row_start, 7, daily['daily_interest_amount'], )
                   

        #             #uom=rec.uom_free_field if rec.uom_free_field else rec.unit_of_measure
        #             #sheet.write(row_start, 3, ' ', )
        #         if daily['date'] :
        #                 if daily['date']==dailyy['value_date']:
        #                     sheet.write(row_start, 4, daily['receipt'], )
        #                     recipt+= daily['receipt']
        #                     sheet.write(row_start, 4, daily['receipt'], )
        #                 else:
        #                     sheet.write(row_start, 4, ' ', )
        #         if daily['value_date']:
        #                 if daily['value_date'].year==dailyy['value_date'].year and daily['value_date'].month==dailyy['value_date'].month  and daily['value_date'].day==dailyy['value_date'].day :
        #                     #sheet.write(row_start, 4, daily['receipt'], )
        #                     inte+= daily['daily_interest_amount']
        #                     penality+=daily['daily_penality_amount']
                            
        #                     sheet.write(row_start, 7, daily['daily_interest_amount'], )
        #                     sheet.write(row_start, 8,daily['daily_penality_amount'], )
        #         if daily['date1']:
        #                 if daily['value_date'].year==dailyy['value_date'].year and daily['value_date'].month==dailyy['value_date'].month  and daily['value_date'].day==dailyy['value_date'].day :
        #                    ppayment+= daily.principal_repayment
        #                    ipayment+=daily.interst_payment
        #                    sheet.write(row_start, 5,daily.principal_repayment, )
        #                    sheet.write(row_start, 9,daily.interst_payment, )

                        
               
                #sheet.write(row_start, 6, daily['principal_repayment'],num_format)
            #eet.write(row_start, 9, daily['principal_repayment'],num_format)
           # tot_amount+=rec.amount
           

                row_start+=1