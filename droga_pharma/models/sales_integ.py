import datetime

from odoo import models, fields, api


class sales_integ(models.Model):
    _inherit = 'sale.order'
    cust_details=fields.Boolean(default=False,string='Customer Details')

    dob=fields.Date('Date of birth',default=datetime.date.today())
    age=fields.Integer(compute='_compute_age')
    sex=fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Sex')
    weight=fields.Float('Weight')
    diagnosis=fields.Html('Diagnosis')

    @api.depends('dob')
    def _compute_age(self):
        for record in self:
            if record.dob:
                today = datetime.date.today()
                # Check if the date has passed this year
                if today.strftime("%m%d") >= record.dob.strftime("%m%d"):
                    record['age'] = today.year - record.dob.year
                else:
                    record['age'] = today.year - record.dob.year - 1
            else:
                record['age'] = 0

    def disp_products(self):
        temp=self.invoice_status
        self.state='dispense'
        self.invoice_status=temp

        #FIX ME - dispense products here

class sales_integ(models.Model):
    _inherit = 'sale.order.line'
    duration=fields.Float('Duration',compute='get_duration',default=1)
    frequency=fields.Float('Frequency',compute='get_freq',default=1)
    rate_type= fields.Selection([("daily", "Daily"), ("weekly", "Weekly"),('monthly','Monthly')],default='daily')

    @api.depends('frequency','product_uom_qty')
    def get_duration(self):
        for rec in self:

            rec.duration = rec.product_uom_qty / rec.frequency if rec.frequency != 0 else 1


    @api.depends('duration', 'product_uom_qty')
    def get_freq(self):
        for rec in self:

            rec.frequency = rec.product_uom_qty / rec.duration if rec.duration != 0 else 1