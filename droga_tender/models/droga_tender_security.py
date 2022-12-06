from odoo import fields, models, api
from datetime import datetime, timedelta

from odoo.exceptions import UserError


class ModelName(models.Model):
    _name = 'droga.tender.security.detail'

    #relation fields
    tender_id=fields.Many2one('droga.tender.master')
    bid_security=fields.Many2one('droga.tender.master')
    performance_security=fields.Many2one('droga.tender.contract')
    advance_security = fields.Many2one('droga.tender.contract')
    security_type=fields.Many2one('droga.tender.settings.sec.type','Security Type')
    security_for=fields.Char('Security for')
    bank = fields.Many2one('res.bank', 'Bank')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    #date fields
    issue_date=fields.Date('Issue date')
    starting_date = fields.Date('Starting date')
    dead_line_date = fields.Date('Deadline date',compute="compute_deadline")
    @api.depends("starting_date","security_period_in_days")
    def compute_deadline(self):
        for record in self:
            if record.starting_date:
                record.dead_line_date=record.starting_date + timedelta (days=record.security_period_in_days)
            else:
                record.dead_line_date=record.starting_date



    #decimal fields
    security_period_in_days=fields.Integer('Security period in days')
    security_amount = fields.Float('Security amount')

    #selection fields
    status=fields.Selection([('Active','Active'),('Expired','Expired'),('Returned','Returned')])

    # Text fields
    bank_number=fields.Char('Bank Number')


