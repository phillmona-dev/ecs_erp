from odoo import fields, models, api


class parentProject(models.Model):
    _name = 'parent.project'

    name = fields.Char()
    location = fields.Many2one('res.partner')


class drogaProject(models.Model):
    _inherit = 'project.project'

    parent_project = fields.Many2one('parent.project')
    project_progress = fields.Float(compute="_project_progress")
    stages_sum=fields.Char('Stages sum',compute='_project_progress')

    def _project_progress(self):
        for record in self:
            record.ensure_one()
            record.project_progress =0
            record.stages_sum=''
            sta_sum=0
            task_list = record.env['project.task.type'].search([('project_ids', '=', record.id)])
            print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
            print(task_list)
            for rec in task_list:
                record.project_progress += (rec.task_stage_progress * rec.task_stage_weight) / 100
                sta_sum += rec.task_stage_weight
            record.stages_sum=str(sta_sum)
