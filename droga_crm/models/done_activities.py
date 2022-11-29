from datetime import date
from string import capwords

from odoo import models,fields,api


class done_activity(models.Model):
    _name = "droga.crm.done.activity"

    name = fields.Char('Summary')
    feedback = fields.Char('Act. feedback')
    source_name=fields.Char('Record name')
    source_id = fields.Integer('Record ID')
    state = fields.Char('State')
    sales_area = fields.Char('Act. area')
    type = fields.Char('Act. type')
    user = fields.Char('User')
    activity_date=fields.Date('Act. planned date')
    action_date = fields.Date('Actual act. date')
    res_model=fields.Char('Record type')
    res_model_descr = fields.Char('Model')
    res_model_id=fields.Integer('Model ID')
    act_note = fields.Text('Act. note')
    act_id=fields.Integer('Activity ID')
    from_visit_plan=fields.Boolean('Visit planned?')


class mail_activity_extension(models.Model):
    _inherit = "mail.activity"

    def unlink(self):
        for rec in self:
            to_update = self.env['droga.crm.done.activity'].search([('act_id', '=', rec.id)])
            if to_update:
                if to_update.state!='Done':
                    to_update.write({'state': 'Cancelled'})
                    to_update.write({'action_date': date.today()})
        return super(mail_activity_extension,self).unlink()

