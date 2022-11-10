from odoo import models, fields, api
from odoo.exceptions import UserError

class droga_tender_sale_line_extension(models.Model):
    _inherit='sale.order.line'
    tender_line=fields.Many2one('droga.tender.performance.evaluation')

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

    droga_product=fields.Many2one('product.template')

    award_cost = fields.Float("Awarded cost")

    perf_pct=fields.Float('% of Performance',compute="compute_performance")

    sales_order=fields.Boolean('Sales ordered',compute="_get_order_status")
    def _get_order_status(self):
        for rec in self:
            if self.env['sale.order.line'].search([('tender_line','=',rec.id)]):
                rec.sales_order=True
            else:
                rec.sales_order = False
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

    def reg_products(self):
        channels = self.env['mail.channel'].search([('name', '=', 'Tender buisness development')])

        message = "Please register product titled '" + self.item_pro + "'."
        message = message + '\n Product group is - ' + self.type_item.type_or_item_name if self.type_item.type_or_item_name else message
        channels[0].message_post(
            subject="Product registration. ",
            body=message,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
            author_id=self.env.user.id,
        )


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