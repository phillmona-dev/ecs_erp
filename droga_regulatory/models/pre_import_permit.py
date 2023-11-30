from datetime import datetime
from odoo import models, fields,api

class PreImportPermit(models.Model):
    _name = 'droga.reg.pre.import.permit.header'
    _description = 'Pre Import Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    manufacturer = fields.Char(string='Manufacturer')
    proforma_invoice_no = fields.Char(string='Proforma Invoice No.')
    invoice_amount = fields.Float(string='Invoice Amount (USD)')
    date_received = fields.Date(string='Date Received')
    date_generated = fields.Date(string='Date Generated')
    app_no = fields.Char(string='App No.')
    discrepancy = fields.Char(string='Discrepancy')

    no_days = fields.Char("Number of days taken", compute='compute_days_between_dates', readonly=True)

    @api.depends('date_received', 'date_generated')
    def compute_days_between_dates(self):
        for record in self:
            if record.date_received and record.date_generated:
                date_format = "%Y-%m-%d"
                datetime1 = datetime.strptime(str(record.date_received), date_format)
                datetime2 = datetime.strptime(str(record.date_generated), date_format)

                delta = datetime2 - datetime1
                num_days = delta.days
                num_of_days = str(num_days) + ' days'
                record.no_days = num_of_days
            else:
                record.no_days = 'Not Set'
