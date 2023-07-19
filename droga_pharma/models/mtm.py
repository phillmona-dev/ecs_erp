from email.policy import default
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class droga_pharma_mtm_header(models.Model):
    _name = 'droga.pharma.mtm.header'
    _rec_name = "client_descr"

    asses_care_plan=fields.Html('Assessment and care plan')
    recs_inter=fields.Html('Recommendations / Interventions')

    plan_generate_frequency=fields.Integer('Plan generation frequency in days')

    detail_mtm=fields.One2many('droga.pharma.mtm.detail','parent_mtm')
    detail_mtm_followup = fields.One2many('droga.pharma.mtm.follow_up', 'parent_mtm_follow')
    # Related fields
    client = fields.Many2one('res.partner',related='sales_origin.partner_id')
    customer = fields.Many2one('droga.pharma.cust.employees',related='sales_origin.customer_emp')
    client_descr= fields.Char(related='sales_origin.emp_descr')
    sales_origin=fields.Many2one('sale.order')

    #dates
    cons_start_date=fields.Date('MTM start date')
    cons_end_date = fields.Date('MTM end date',compute='_get_cons_end_date')

    def _get_cons_end_date(self):
        for rec in self:
            rec.cons_end_date=rec.cons_start_date

    def mtm_schedule(self):
        return

    @api.model
    def create(self, vals):
        res=super(droga_pharma_mtm_header, self).create(vals)
        if not res.customer:
            raise ValidationError(
                "Customer must be registered to initiate an MTM order.")
        return res

class droga_pharma_mtm_detail(models.Model):
    _name = 'droga.pharma.mtm.detail'

    parent_mtm=fields.Many2one('droga.pharma.mtm.header')

    # Text fields
    indication = fields.Char("Indication", required=True)
    drug = fields.Many2one('product.template', string='Drug')
    frequency = fields.Char("Frequency")
    frequency_type = fields.Selection([("Hourly", "Hourly"),("Daily", "Daily"), ("Weekly", "Weekly"), ('Monthly', 'Monthly')], default='Daily',string='Rate')
    start_date = fields.Date('Start date')
    stop_date = fields.Date('Stop date')

class droga_pharma_mtm_schedule(models.Model):
    _name = 'droga.pharma.mtm.follow_up'

    parent_mtm_follow = fields.Many2one('droga.pharma.mtm.header')

    date_follow_up=fields.Date('Follow up date')
    time=fields.Char('Follow up time')
    current_status=fields.Many2one('droga.pharma.current_status',string='Current status')

    follow_up_detail=fields.One2many('droga.pharma.mtm.follow_up.detail','parent_follow_up')

    eff_saf_med = fields.Html('Effectiveness and safety of medication')
    int_imple = fields.Html('Intervention implemented')

    def open_follow_up_form(self):
        return {
            'name': 'Follow up',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.pharma.mtm.follow_up',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.id
        }


class droga_pharma_mtm_schedule_detail(models.Model):
    _name = 'droga.pharma.mtm.follow_up.detail'
    parent_follow_up=fields.Many2one('droga.pharma.mtm.follow_up')

    drug_therapy_problem = fields.Many2one('droga.pharma.drug.therapy.problem', string='Drug therapy problem')
    drug_therapy_cause = fields.Many2one('droga.pharma.drug.therapy.problem.cause', string='Drug therapy cause',
                                         domain="[('problem_id','=',drug_therapy_problem)]")
    intervention = fields.Char('Intervention', compute='_get_default_intervention', store=True,
                               inverse='_inverse_function')
    def _inverse_function(self):
        pass
    @api.depends('drug_therapy_cause')
    def _get_default_intervention(self):
        for rec in self:
            rec.intervention=rec.drug_therapy_cause.recommended_intervention.descr

    intervention_implemented = fields.Boolean('Intervention implemented?')

    asses_care_plan = fields.Html('Assessment and care plan',
                                  related='parent_follow_up.parent_mtm_follow.asses_care_plan')

    recs_inter = fields.Html('Recommendations / Interventions',
                             related='parent_follow_up.parent_mtm_follow.recs_inter')
    client = fields.Many2one('res.partner', related='parent_follow_up.parent_mtm_follow.client')
    customer = fields.Many2one('droga.pharma.cust.employees', related='parent_follow_up.parent_mtm_follow.customer')

    indication = fields.Char("Indication", compute='get_indication')

    def get_indication(self):
        for fu in self:
            ind = ''
            for fud in fu.parent_follow_up.parent_mtm_follow.detail_mtm:
                ind = ind + fud.indication + ', '
            fu.indication = ind

    drug = fields.Char("Drug", compute='get_drugs')

    def get_drugs(self):
        for followup in self:
            followup.drug = '-'
            # Write the functio similar to indication here

    remark = fields.Char('Remark')
