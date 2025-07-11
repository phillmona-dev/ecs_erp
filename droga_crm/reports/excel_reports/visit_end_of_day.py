from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
from datetime import date
from odoo.exceptions import UserError
from base64 import encodebytes
import base64
import tempfile

from odoo.http import request
from odoo.tools import groupby


class crm_end_of_day(models.TransientModel):
    _name = 'droga.crm.eod.wizard'
    _description = 'End of day Report Wizard'

    date_to = fields.Date('Date', required=True, default=lambda self: fields.Date.today())
    employee_id = fields.Many2one('droga.pro.sales.master', string='Sales rep',default='_get_pr_sales_logged', required=True)

    all_emps=fields.Boolean('All Employees',default=False)

    fileout = fields.Binary('File', readonly=True)
    filename = fields.Char('Filename')

    def _get_pr_sales_logged(self):
        if not request:
            return False
        ses = self.env['droga.pro.sales.master.visit'].search([('s_id', '=', request.session.sid)])
        return False if len(ses)==0 else ses[0].pro_id.ids[0]

    def action_generate_report(self):
        if not self.employee_id:
            raise UserError("Please select an employee.")

        if self.all_emps:
            leads = self.env['droga.crm.done.activity'].search([
                ('activity_date', '=', self.date_to),
            ])
        else:
            leads = self.env['droga.crm.done.activity'].search([
                ('activity_date', '=', self.date_to),
                ('sales_rep', '=', self.employee_id.id)
            ])


        file_io = BytesIO()
        workbook = xlsxwriter.Workbook(file_io)
        self._generate_xlsx(workbook, leads)
        workbook.close()
        file_io.seek(0)

        self.fileout = encodebytes(file_io.read())
        if not self.all_emps:
            self.filename = f"EOD_Report_{self.employee_id.p_name}_{self.date_to}.xlsx"
        else:
            self.filename = f"EOD_Report_ALL_{self.date_to}.xlsx"

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=fileout&download=true&filename={self.filename}",
            'target': 'new',
        }

    def _generate_xlsx(self, workbook, leadsall):
        sheet = workbook.add_worksheet('EOD Report')

        bold = workbook.add_format({'bold': True, 'font_size': 12})
        header_bold = workbook.add_format({'bold': True, 'font_size': 14})
        center = workbook.add_format({'align': 'center'})
        center_bold = workbook.add_format({'bold': True, 'align': 'center','valign':'vcenter', 'font_size': 12})
        wrap = workbook.add_format({'text_wrap': True})
        border = workbook.add_format({'border': 1})
        company_name_format = workbook.add_format({
            'bold': True,
            'font_size': 24,
            'align': 'center',
            'valign': 'bottom'
        })
        title_format = workbook.add_format({
            'bold': 1,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        gray_color = workbook.add_format({
            'bold': 0,
            'border': 0,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 11,
            'text_wrap': 1,
            'fg_color': '#F6F5F5'})
        sheet.set_row(0, 70)
        sheet.set_row(1, 30)

        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 25)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 10)
        sheet.set_column('G:G', 12)
        sheet.set_column('H:H', 15)

        agents = leadsall.mapped('sales_rep').sorted(key=lambda r:r.p_name)

        rs = 1
        for agent in agents:
            lead=leadsall.filtered(lambda r: r.sales_rep.id==agent.id)
            rs = 5 + self.gen_emp(lead, sheet, rs, company_name_format, center_bold, bold, title_format,
                                           gray_color)

    def gen_emp(self,leads,sheet,rs,company_name_format,center_bold,bold,title_format,gray_color):
        row_start = rs

        company = self.env.company
        if company.logo_web:
            logo_data = base64.b64decode(company.logo_web)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(logo_data)
                tmp.flush()
                sheet.insert_image('A' + str(row_start), tmp.name,
                                   {'x_scale': 1.2, 'y_scale': 1, 'x_offset': 5, 'y_offset': 5})

        sheet.set_row(row_start-1, 70)
        sheet.set_row(row_start, 30)
        sheet.merge_range('B' + str(row_start) + ':H' + str(row_start), 'Droga Pharma PLC', company_name_format)
        row_start = row_start + 1
        sheet.merge_range('B' + str(row_start) + ':H' + str(row_start), 'Daily Activity Report', center_bold)
        row_start = row_start + 2
        sheet.write('A' + str(row_start), 'Med/Sales rep:', bold)
        sheet.write('B' + str(row_start), leads[0].sales_rep.p_name)
        row_start = row_start + 1
        sheet.write('A' + str(row_start), 'CRM Team:', bold)
        sheet.write('B' + str(row_start), leads[0].sales_rep.team.name)
        sheet.write('D' + str(row_start), 'Date', bold)
        sheet.write('E' + str(row_start), str(self.date_to))

        mornings = leads.filtered(lambda r: r.lead_id.planned_visit_selection in ('2-4 seat', '4-6 seat', '6-7 seat'))
        if len(mornings) > 0:
            sheet.set_row(row_start, 30)
            row_start = row_start + 1
            sheet.merge_range('A' + str(row_start) + ':H' + str(row_start), 'Morning Activity', title_format)
            row_start = row_start + 1
            sheet.write('A' + str(row_start), 'Institution', gray_color)
            sheet.write('B' + str(row_start), 'Doctor / contact', gray_color)
            sheet.write('C' + str(row_start), 'Products', gray_color)
            sheet.write('D' + str(row_start), 'Check in', gray_color)
            sheet.write('E' + str(row_start), 'Check out', gray_color)
            sheet.write('F' + str(row_start), 'Duration', gray_color)
            sheet.write('G' + str(row_start), 'Planned?', gray_color)
            sheet.write('H' + str(row_start), 'Status', gray_color)

            for lead in mornings:
                sheet.write(row_start, 0, lead.lead_id.partner_id.name)
                sheet.write(row_start, 1, (
                            lead.lead_id.contact_custom2.contact_name + '-' + lead.lead_id.contact_custom2.specialty.specialty) if lead.lead_id.contact_custom2 else ' ')
                prods = ''
                for prod in lead.lead_id.core_products:
                    prods = prods + prod.name + ' '
                sheet.write(row_start, 2, prods if prods else ' ')
                sheet.write(row_start, 3, lead.check_in if lead.check_in else ' ')
                sheet.write(row_start, 4, lead.check_out if lead.check_out else ' ')
                # TODO
                sheet.write(row_start, 6, lead.from_visit_plan_str + (
                    ('-' + lead.lead_id.planned_visit_selection) if lead.lead_id.planned_visit_selection else ' '))
                sheet.write(row_start, 7, lead.state)
                row_start = row_start + 1

        afternoons = leads.filtered(lambda r: r.lead_id.planned_visit_selection in ('7-9 seat', '9-11 seat'))
        if len(afternoons) > 0:
            sheet.set_row(row_start, 30)
            row_start = row_start + 1
            sheet.merge_range('A' + str(row_start) + ':H' + str(row_start), 'Afternoon Activity', title_format)
            row_start = row_start + 1

            sheet.write('A' + str(row_start), 'Institution', gray_color)
            sheet.write('B' + str(row_start), 'Doctor / contact', gray_color)
            sheet.write('C' + str(row_start), 'Products', gray_color)
            sheet.write('D' + str(row_start), 'Check in', gray_color)
            sheet.write('E' + str(row_start), 'Check out', gray_color)
            sheet.write('F' + str(row_start), 'Duration', gray_color)
            sheet.write('G' + str(row_start), 'Planned?', gray_color)
            sheet.write('H' + str(row_start), 'Status', gray_color)

            for lead in afternoons:
                sheet.write(row_start, 0, lead.lead_id.partner_id.name)
                sheet.write(row_start, 1, (
                        lead.lead_id.contact_custom2.contact_name + '-' + lead.lead_id.contact_custom2.specialty.specialty) if lead.lead_id.contact_custom2 else ' ')
                prods = ''
                for prod in lead.lead_id.core_products:
                    prods = prods + prod.name + ' '
                sheet.write(row_start, 2, prods if prods else ' ')
                sheet.write(row_start, 3, lead.check_in if lead.check_in else ' ')
                sheet.write(row_start, 4, lead.check_out if lead.check_out else ' ')
                # TODO
                sheet.write(row_start, 6, lead.from_visit_plan_str)
                sheet.write(row_start, 7, lead.state)
                row_start = row_start + 1

        return row_start
