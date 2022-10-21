from odoo import models, fields, api
from odoo.exceptions import UserError

class droga_tender_master(models.Model):
    _name = 'droga.tender.performance.evaluation'

    # Text fields
    lot_number = fields.Char("Lot number")
    item_des = fields.Char("Item description")

    # decimal fields
    quantity = fields.Float("Quantity")
    unit_price = fields.Float("Unit price")
    amount = fields.Float("Amount quoted", compute="compute_amount")

    award_cost = fields.Float("Awarded cost")

    @api.depends("unit_price", "quantity")
    def compute_amount(self):
        for rec in self:
            rec.amount = rec.unit_price * rec.quantity
            if rec.award_cost==0:
                rec.award_cost=rec.amount
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
    type_item = fields.Many2one('droga.tender.settings.type.item', string='Type or items')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})

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

    @api.model
    def create(self, vals_list):
        if vals_list["quantity"]==0:
            raise UserError("Quantity can not be zero.")
        return super().create(vals_list)

    def write(self, vals):
        if 'quantity' in vals:
            if vals["quantity"]==0:
                raise UserError("Quantity can not be zero.")
        return super().write(vals)