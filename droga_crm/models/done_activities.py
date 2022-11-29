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

    @api.model
    def create(self, vals_list):
        done_act = self.env['droga.crm.done.activity']
        res=super(mail_activity_extension, self).create(vals_list)

        for activity in res:
            #mod_des='Lead' if activity.res_model_id=='Lead' and
            done_act.create(
                {'name': activity.summary, 'activity_date': activity.date_deadline, 'type': activity.activity_type_id.name,'from_visit_plan':True if (activity.res_model_id.model=='crm.lead' and self.env['crm.lead'].search([('id','=',activity.res_id)]).plan_id) else False,
                 'state': 'Open', 'source_name': activity.res_name,'act_id':activity.id,'source_id':activity.res_id,'sales_area':self.env['crm.lead'].search([('id','=',activity.res_id)]).partner_id.city_name.city_descr if activity.res_model_id.model=='crm.lead' else activity.res_model_id.name,
                 'res_model_id': activity.res_model_id,'res_model_descr':capwords(self.env['crm.lead'].search([('id','=',activity.res_id)]).type) if activity.res_model_id.model=='crm.lead' else activity.res_model_id.name, 'act_note': activity.note if activity.note else '', 'res_model': activity.res_model,
                 'user': activity.user_id.name})
        return res

    def unlink(self):
        for rec in self:
            to_update = self.env['droga.crm.done.activity'].search([('act_id', '=', rec.id)])
            if to_update:
                if to_update.state!='Done':
                    to_update.write({'state': 'Cancelled'})
                    to_update.write({'action_date': date.today()})
        return super(mail_activity_extension,self).unlink()

    def action_feedback(self,feedback=False, attachment_ids=None):
        for rec in self:
            to_update=self.env['droga.crm.done.activity'].search([('act_id','=',rec.id)])
            if to_update:
                to_update.write({'state':'Done'})
                to_update.write({'action_date': date.today()})
                if feedback:
                    to_update.write({'feedback': feedback})

                    #visits_remark_dto_update=self.env['droga.crm.contacts.schedule'].search([('leads.id','=',to_update.source_id)])
                    #for visit in visits_remark_dto_update:
                    #    if not visit.sales_close_descr:
                    #        visit.sales_close_descr=feedback

        return super(mail_activity_extension, self).action_feedback(feedback=False, attachment_ids=None)
