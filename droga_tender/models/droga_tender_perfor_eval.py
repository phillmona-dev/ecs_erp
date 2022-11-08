from odoo import models, fields, api
from odoo.exceptions import UserError

class droga_tender_master(models.Model):
    _name = 'droga.tender.performance.evaluation'

    # Text fields
    lot_number = fields.Char("Lot number",related='parent_tender_performance_detail.lot_number')
    item_des = fields.Char("Item requested",related='parent_tender_performance_detail.item_des')
    item_pro = fields.Char("Item proposed",related='parent_tender_performance_detail.item_pro')

    # decimal fields
    quantity = fields.Float("Quantity",related='parent_tender_performance_detail.quantity')
    unit_price = fields.Float("Unit price",related='parent_tender_performance_detail.unit_price')
    amount = fields.Float("Amount quoted",related='parent_tender_performance_detail.amount')

    award_cost = fields.Float("Awarded cost")

    perf_pct=fields.Float('% of Performance',compute="compute_performance")
    @api.depends("amount", "award_cost")
    def compute_performance(self):
        for rec in self:
            try:
                rec.perf_pct = (rec.award_cost / rec.amount) * 100
            except Exception as e:
                rec.perf_pct=0.0

    # relational fields
    unit_of_measure = fields.Many2one('uom.uom', string='UOM')
    parent_tender_performance = fields.Many2one('droga.tender.master', required=True)
    parent_tender_performance_detail = fields.Many2one('droga.tender.submission.detail')
    type_item = fields.Many2one('droga.tender.settings.type.item', string='Type or items',related='parent_tender_performance_detail.type_item')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]},related='parent_tender_performance_detail.company_id')

    def competitors_open(self):
        return {
            'name': 'Competitors',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.tender.performance.evaluation',
            'view_id': self.env.ref('droga_tender.droga_tender_perf_eval_view_tree').id,
            'type': 'ir.actions.act_window',

            #This will pass the detail ID if a record is present
            'res_id': self.id,

            #When target is new, it will popup else it will use it's own form, wow ferenj
            'target': 'new',


        }

    def sales_order_open(self):
        return {
            'name': 'Sales order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': self.env.ref('sale.view_order_form').id,
            'type': 'ir.actions.act_window',
            'context': {
                'default_tender_origin_form': self.parent_tender_performance.id,
                'default_partner_id': self.parent_tender_performance.customer.master_cust_id.id,
            }
        }

    @api.model
    def create(self, vals_list):
        if vals_list["award_cost"]==0:
            raise UserError("Awarded cost can not be zero.")
        return super().create(vals_list)

    def write(self, vals):
        if 'award_cost' in vals:
            if vals["award_cost"]==0:
                raise UserError("Awarded cost can not be zero.")
        return super().write(vals)