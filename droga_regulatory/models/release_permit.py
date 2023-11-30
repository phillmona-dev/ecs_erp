from datetime import datetime
from odoo import models, fields, api

class PreImportPermitGenerated(models.Model):
    _name = 'droga.reg.pre.import.permit.generated'
    _description = 'Pre Import Permit Generated'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    manufacturer = fields.Char(string='Manufacturer')
    invoice_amount = fields.Float(string='Amount Invoiced')

    preimport_permit_no = fields.Char(string='Preimport permit No')
    commercial_invoice_no = fields.Char(string='Commercial Invoice No')

    date_generated = fields.Date(string='Generated On')
    date_approved = fields.Date(string='Approved On')
    date_received = fields.Date(string='Received On')
    date_released = fields.Date(string='Released On')

    encountered_problem = fields.Char(string='Comment')
    no_days = fields.Char("Number of days taken", compute='compute_days_between_dates', readonly=True)

    @api.depends('date_received', 'date_approved')
    def compute_days_between_dates(self):
        for record in self:
            if record.date_received and record.date_approved:
                date_format = "%Y-%m-%d"
                datetime1 = datetime.strptime(str(record.date_received), date_format)
                datetime2 = datetime.strptime(str(record.date_approved), date_format)

                delta = datetime2 - datetime1
                num_days = delta.days
                num_of_days = str(num_days) + ' days'
                record.no_days = num_of_days
            else:
                record.no_days = 'Not Set'
