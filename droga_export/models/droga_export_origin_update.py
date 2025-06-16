from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class droga_export_status(models.Model):
    _name='droga.export.origin.update'
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    pay_req_to_update=fields.Many2one('droga.account.payment.request',string='Payment request No')
    sales_from = fields.Many2one('sale.order', string='Sales from')
    sales_to=fields.Many2one('sale.order', string='Sales to')
    cleaning_unit_from=fields.Many2one('droga.inventory.consignment.issue',string='Cleaning unit from')
    cleaning_unit_to = fields.Many2one('droga.inventory.consignment.issue', string='Cleaning unit to')
    status = fields.Selection(
        [('Draft', 'Draft'), ('Done', 'Done')], default="Draft")

    def update_pay(self):
        for rec in self:
            if not rec.sales_to:
                raise ValidationError(
                    "Please enter sales to field, it's mandatory.")
            rec.pay_req_to_update.write({'export_origin_form': rec.sales_to.id})
            rec.pay_req_to_update.write({'issue_export_origin_form': rec.cleaning_unit_to.id})
            rec.status="Done"

    @api.onchange('pay_req_to_update')
    def populatefields(self):
        for rec in self:
            rec.sales_from=rec.pay_req_to_update.export_origin_form.id
            rec.sales_to = rec.pay_req_to_update.export_origin_form.id
            rec.cleaning_unit_from = rec.pay_req_to_update.issue_export_origin_form.id
            rec.cleaning_unit_to = rec.pay_req_to_update.issue_export_origin_form.id

    @api.onchange('sales_to')
    def clear_clean_unit_to(self):
        for rec in self:
            rec.cleaning_unit_to=False

class droga_export_po_status(models.Model):
    _name='droga.export.po.origin.update'
    po_to_update=fields.Many2one('purchase.order',string='Purchase Order')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    sales_from = fields.Many2one('sale.order', string='Sales from')
    sales_to=fields.Many2one('sale.order', string='Sales to')
    #cleaning_unit_from=fields.Many2one('droga.inventory.consignment.issue',string='Cleaning unit from')
    #cleaning_unit_to = fields.Many2one('droga.inventory.consignment.issue', string='Cleaning unit to')
    status = fields.Selection(
        [('Draft', 'Draft'), ('Done', 'Done')], default="Draft")

    def update_pay(self):
        for rec in self:
            if not rec.sales_to:
                raise ValidationError(
                    "Please enter sales to field, it's mandatory.")
            rec.po_to_update.write({'export_origin_form': rec.sales_to.id})
            rec.status="Done"

    @api.onchange('po_to_update')
    def populatefields(self):
        for rec in self:
            rec.sales_from=rec.po_to_update.export_origin_form.id
            rec.sales_to = rec.po_to_update.export_origin_form.id



