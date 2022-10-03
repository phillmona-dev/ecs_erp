from odoo import models, fields,api
from odoo.exceptions import UserError


class droga_tender_submission_detail(models.Model):
    _name = 'droga.tender.submission.detail'

    #Selection fields
    tech_result = fields.Selection([('Pass', 'Pass'), ('Fail', 'Fail')])
    status = fields.Selection([('awarded', 'Awarded'), ('cancelled', 'Cancelled'),('undeva', 'Under evaluation'),('faiten', 'Failed tender'),('lost', 'Lost')])

    #Text fields
    lot_number=fields.Char("Lot Number",required=True)
    item_des = fields.Char("Item Description")
    brand_model = fields.Char("Brand/Model")
    remark = fields.Char("Description and remark")
    award_fold_num = fields.Char("Award folder number")

    # decimal fields
    quantity=fields.Float("Quantity",default=1)
    unit_price = fields.Float("Unit Price")
    amount = fields.Float("Amount",compute="compute_amount")
    @api.depends("unit_price","quantity")
    def compute_amount(self):
        for rec in self:
            rec.amount=rec.unit_price*rec.quantity
    deliv_period = fields.Float("Delivery days")

    # relational fields
    type_item = fields.Many2one('droga.tender.settings.type.item', string='Type or items',required=True)
    parent_tender_submission=fields.Many2one('droga.tender.master',required=True)
    unit_of_measure=fields.Many2one('uom.uom', string='UOM')
    currency=fields.Many2one('res.currency',string='Currency')
    supplier=fields.Many2one('res.partner',string='Supplier')
    country = fields.Many2one('res.country', string='Country')
    incoterm=fields.Many2one('droga.tender.settings.incoterm','Incoterm')
    competi_id = fields.One2many('droga.tender.competitors', 'submission_id')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 state={'done': [('readonly', True)]})

    # Date fields
    fin_open = fields.Datetime("Financial opening GRE")
    st_date = fields.Date("Status date GRE")

    def competitors_open(self):
        return {
            'name': 'Competitors',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.tender.submission.detail',
            'view_id': self.env.ref('DROGA_TENDER.droga_tender_competitors_view_tree').id,
            'type': 'ir.actions.act_window',

            # This will pass the detail ID if a record is present
            'res_id': self.id,

            # When target is new, it will popup else it will use it's own form, wow ferenj
            'target': 'new',

        }

    @api.model
    def create(self, vals_list):
        if vals_list["quantity"]==0:
            raise UserError("Quantity can not be zero.")

        if vals_list["status"]=="awarded":
            to_create_perf_eval = {
                    "lot_number": vals_list["lot_number"],
                    "quantity": vals_list["quantity"],
                    "type_item": vals_list["type_item"],
                    "item_des":vals_list["item_des"],
                    "parent_tender_performance": vals_list["parent_tender_submission"],
                }
            self.env["droga.tender.performance.evaluation"].create(to_create_perf_eval)

            to_create_cont_agreement = {
                "lot_number": vals_list["lot_number"],
                "type_item": vals_list["type_item"],
                "item_des": vals_list["item_des"],
                "parent_tender_contract": vals_list["parent_tender_submission"],
            }
            self.env["droga.tender.contract"].create(to_create_cont_agreement)

        return super().create(vals_list)

    def write(self, vals):
        if 'status' not in vals:
            return super().write(vals)
        if 'quantity' in vals:
            if vals["quantity"]==0:
                raise UserError("Quantity can not be zero.")
        if vals["status"]=="awarded":
            to_create_perf_eval = {
                "lot_number": self.lot_number,
                "quantity": self.quantity,
                "type_item": self.type_item.id,
                "item_des": self.item_des,
                "parent_tender_performance": self.parent_tender_submission.id,
            }
            self.env["droga.tender.performance.evaluation"].create(to_create_perf_eval)

            to_create_cont_agreement = {
                "lot_number": self.lot_number,
                "type_item": self.type_item.id,
                "item_des": self.item_des,
                "parent_tender_contract": self.parent_tender_submission.id,
            }
            self.env["droga.tender.contract"].create(to_create_cont_agreement)
        return super().write(vals)