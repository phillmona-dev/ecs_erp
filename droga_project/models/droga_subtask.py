from odoo import fields, models, api


class drogaSubTask(models.Model):
    _inherit = 'project.task'

    task_progress = fields.Float(compute='_task_weight', store=True)
    sum_of_tasks = fields.Float(compute='_task_weight', string="Sum Of Task weight", store=True)
    task_editable = fields.Boolean(compute='_compute_editable', store=True)
    task_weight = fields.Float()

    @api.depends('child_ids')
    def _compute_editable(self):
        for rec in self:
            if rec.child_ids:
                rec.task_editable = False
            else:
                rec.task_editable = True

    def _task_editable(self, operator, value):
        if operator == '=':
            tasks = self.env['project.task'].search([('child_ids', '=', False)])
            if len(tasks) == 0:
                has_childs = self.env['project.task'].sudo().search([('child_ids', '=', False)])
                return [('id', 'in', [x.id for x in has_childs] if has_childs else False)]
            else:
                return [('id', 'in', [])]
        else:
            return [('id', 'in', [])]

    @api.depends('child_ids', 'child_ids.child_ids', 'child_ids.child_ids.child_ids',
                 'child_ids.child_ids.child_ids.child_ids', 'child_ids.child_ids.child_ids.child_ids.child_ids',
                 'child_ids.child_ids.child_ids.child_ids.child_ids.child_ids',
                 'child_ids.child_ids.child_ids.child_ids.child_ids.child_ids.child_ids',
                 'child_ids.task_weight', 'child_ids.child_ids.task_weight',
                 'child_ids.child_ids.child_ids.task_weight',
                 'child_ids.child_ids.child_ids.child_ids.task_weight',
                 'child_ids.child_ids.child_ids.child_ids.child_ids.task_weight',
                 'child_ids.child_ids.child_ids.child_ids.child_ids.child_ids.task_weight',
                 'child_ids.child_ids.child_ids.child_ids.child_ids.child_ids.child_ids.task_weight'
                 )
    def _task_weight(self):
        task_progress = 0.00000
        for record in self:
            record.task_progress = 0
            record.sum_of_tasks = 0
            for rec in record.child_ids:
                record.task_progress += (rec.task_weight * rec.task_progress) / 100
                record.sum_of_tasks += rec.task_weight
                if record.task_progress == 100:
                    self.stage_id.name = 'Development'

    def local_purchase(self):
        return {
            'name': 'Local Purchase',
            'view_type': 'tree',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_subtask_reference': self.id,
                # 'default_issue_type': 'SIF'
            },
            'domain':
                ([('subtask_reference', '=', self.id)])
        }

    def stockRequest(self):
        return {
            'name': 'Stock Request',
            'view_type': 'tree',
            'view_mode': 'tree,form',
            'res_model': 'droga.inventory.office.supplies.request',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_stock_request_reference': self.id,
                # 'default_issue_type': 'SIF'
            },
            'domain':
                ([('stock_request_reference', '=', self.id)])
        }

    def taskPaymentRequest(self):
        return {
            'name': 'Task Payment Request',
            'view_type': 'tree',
            'view_mode': 'tree,form',
            'res_model': 'droga.account.payment.request',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_task_payment_request_reference': self.id,
                # 'default_issue_type': 'SIF'
            },
            'domain':
                ([('task_payment_request_reference', '=', self.id)])
        }


class droga_subtask_local_purchase(models.Model):
    _inherit = 'purchase.order'

    subtask_reference = fields.Many2one('project.task', readonly=True)


class droga_stock_request(models.Model):
    _inherit = 'droga.inventory.office.supplies.request'
    stock_request_reference = fields.Many2one('project.task', readonly=True)


class droga_task_stage_progress(models.Model):
    _inherit = 'project.task.type'
    task_stage_weight = fields.Float()
    task_stage_progress = fields.Float(compute='_task_stage_progress')
    task_sum = fields.Float(compute='_task_stage_progress', string="Sum of Task Weight under this stage")

    def _task_stage_progress(self):
        for record in self:
            task_list = record.env['project.task'].search([('stage_id', '=', record.id), ('parent_id', '=', False)])
            record.task_stage_progress = 0
            if task_list:
                for rec in task_list:
                    record.task_stage_progress += (rec.task_progress * rec.task_weight) / 100
                    record.task_sum += rec.task_weight
            else:
                record.task_stage_progress = 0

            print('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
            print(record.name)
            print(record.task_stage_progress)


class droga_task_payment_request(models.Model):
    _inherit = 'droga.account.payment.request'
    task_payment_request_reference = fields.Many2one('project.task', readonly=True)
