from odoo import models,fields

class customer_visit(models.Model):
    _name='droga.customer.visit'
    visit_client=fields.Many2one('res.partner','Customer')
    visit_contact = fields.Many2one('res.partner',string='Contact')
    visit_date=fields.Date('Visit Date')
    planned_visit_time_from=fields.Float('Planned visit time from')
    planned_visit_time_to = fields.Float('Planned visit time to')
    actual_visit_time_from = fields.Float('Actual visit time from')
    actual_visit_time_to = fields.Float('Actual visit time to')
    remark = fields.Char('Remark')

