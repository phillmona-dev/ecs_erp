from odoo import fields, models, api
from odoo.exceptions import UserError
import logging
import pdfkit
import base64

_logger = logging.getLogger(__name__)

class DrogaHealthScreening(models.Model):
    _name = 'droga.health.screening'
    _description = "Droga Pharma Form"

    client_id = fields.Many2one('res.partner.pharma2',string='Name',required=True)
    age = fields.Integer(string="Age")
    mobile = fields.Char(string="Mobile Number", compute="_compute_mobile", store=True)
    sex = fields.Selection([('female', 'Female'), ('male', 'Male')], string="Sex")
    patient_condition = fields.Char(string="Patient Condition")
    weight = fields.Float(string="Weight (KG)")
    bp_systolic = fields.Integer(string="Systolic BP (mmHg)")
    bp_diastolic = fields.Integer(string="Diastolic BP (mmHg)")
    fasting_glucose = fields.Float(string="Fasting Blood Glucose (mg/dL)")
    rbs_glucose = fields.Float(string="Postprandial Blood Glucose (mg/dL)")
    sale_order_id = fields.Many2one('sale.order', string="Sales Order")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    order_from = fields.Char(related='sale_order_id.order_from')

    wareh = fields.Many2one('stock.warehouse', string='Pharmacy Branch', compute='_get_pharma_wh',
                            store=True)
    screening_type = fields.Selection([
        ('glucose', 'Glucose Test'),
        ('bp', 'Blood Pressure Test'),
        ('weight', 'Weight Measurement')
    ], string="Screening Type", required=True)

    @api.depends('client_id', 'sale_order_id', 'screening_type')
    def _get_pharma_wh(self):
        for rec in self:
            if rec.sale_order_id:
                # If there's a sales order, use its warehouse logic
                if rec.sale_order_id.order_from == "PH":
                    rec.wareh = self.env.user.warehouse_ids_ph_disp[
                        0].id if self.env.user.warehouse_ids_ph_disp else False
                elif rec.sale_order_id.order_from == "PT":
                    rec.wareh = self.env.user.warehouse_ids_pt_disp[
                        0].id if self.env.user.warehouse_ids_pt_disp else False
                else:
                    rec.wareh = self.env.user.warehouse_ids_im_ws[0].id if self.env.user.warehouse_ids_im_ws else False
            elif rec.screening_type == "bp":
                # If it's a BP screening and there's no sales order, assign pharmacy warehouse
                rec.wareh = self.env.user.warehouse_ids_ph_disp[0].id if self.env.user.warehouse_ids_ph_disp else False
            else:
                rec.wareh = False

    @api.depends('client_id.partner.mobile', 'client_id.partner.phone')
    def _compute_mobile(self):
        for rec in self:
            if rec.client_id and rec.client_id.partner:
                mobile = rec.client_id.partner.mobile or rec.client_id.partner.phone or ''
                rec.mobile = mobile.replace(" ", "").replace("251", "0")  # Format phone number
            else:
                rec.mobile = ''


    @api.onchange('fasting_glucose', 'rbs_glucose')
    def _onchange_glucose_fields(self):
        if self.fasting_glucose:
            self.rbs_glucose = False
        if self.rbs_glucose:
            self.fasting_glucose = False


    def action_create_payment(self):

        self.ensure_one()
        sale_order = self.sale_order_id

        if sale_order and sale_order.state != 'draft':
            sale_order = sale_order.copy({'state': 'draft'})
            self.write({'sale_order_id': sale_order.id})


        if sale_order:
            return {
                'name': 'Sales Order',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'view_id': self.env.ref('droga_pharma.view_order_form_pharma').id,
                'type': 'ir.actions.act_window',
                'res_id': sale_order.id,
            }

        if not self.client_id or not self.client_id.partner:
            raise UserError("Please select a valid customer before creating the sales order.")

        customer = self.client_id.partner

        default_product = self.env['product.product'].search([('id', '=', 40960)], limit=1)
        if not default_product:
            raise UserError("No products available in the catalog. Please add at least one saleable product.")

        sale_order_vals = {
            'partner_id': customer.id,
            'partner_custom': self.client_id.id,
            'client_order_ref': self.client_id.name,
            'order_line': [(0, 0, {
                'product_id': default_product.id,
                'name': default_product.name,
                'product_uom': default_product.uom_id.id,
                'product_uom_qty': 1,
                'price_unit': 120.0,
            })],
            'state': 'draft',
            'payment_term_id': 11,
            'date_order': fields.Datetime.now(),
            'order_from': 'PH',
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        self.write({'sale_order_id': sale_order.id})


        return {
            'name': 'Sales Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': self.env.ref('droga_pharma.view_order_form_pharma').id,
            'type': 'ir.actions.act_window',
            'res_id': sale_order.id,
        }
