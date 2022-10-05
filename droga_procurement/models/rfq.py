from email.policy import default
from turtle import pu
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class Rfq(models.Model):

    _name = 'droga.purhcase.request.rfq'
    _description = 'Request for Quotation'
    _order = "name desc"

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char('Request Reference', required=True,
                       index=True, copy=False, default='New')
    purhcase_request_id = fields.Many2one(
        "droga.purhcase.request", required=True)
    request_type = fields.Selection(
        related="purhcase_request_id.request_type", store=True)

    date = fields.Datetime("Date", required=True)
    rfq_lines = fields.One2many(
        'droga.purhcase.request.rfq.line', 'rfq_id', required=True)
    remark = fields.Html("Remark")
    technical_remark = fields.Html("Technical remark")

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id', string="Currency", readonly=True,
                                  required=True, store=False)

    procurement_committee = fields.Many2many("hr.employee")

    rfq_foregin_status = fields.One2many(
        "droga.purchase.foregin.status", "rfq_id")

    lcs = fields.One2many('droga.purchase.lc', 'rfq_id')

    state = fields.Selection(
        [("Draft", "Draft"), ("Winner Picked", "Winner Picked"), ("Checked", "Checked"), ("Committee Approval", "Committee Approved"), ("CEO Approval", "CEO Approved"), ("Cancel", "Canceled")], default="Draft", tracking=True)

    # total winner amount
    total_winner_amount = fields.Float(
        "Total Winner Amount", compute="_compute_total_winner_amount", store=True, default=0)

    @api.depends('rfq_lines','purhcase_request_id','state')
    def _compute_total_winner_amount(self):
        for record in self:
            for r in record.rfq_lines:
                if r.winner == "Yes":
                    record.total_winner_amount += r.price_total

    # draft request
    def draft_request(self):
        self.write({'state': 'Draft'})
        return True

    # checked
    def checked(self):
        self.write({'state': 'Checked'})
        return True

    # Committee Approval
    def committee_approval(self):
        self.write({'state': 'Committee Approval'})
        return True

    # ceo approval
    def ceo_approval(self):
        self.write({'state': 'CEO Approval'})
        self.load_foregin_rfq_status()
        return True

    def load_foregin_rfq_status(self):
        # get phase 1 or request for quotation steps
        rfq_steps = self.env["droga.foregin.purchase.phases"].search([])

        for rfq_step in rfq_steps:
            # create record in rfq step status one2manyobject
            status = {'rfq_id': self.id,
                      'phase': rfq_step.id,
                      'status': 'Not Started'}
            # create the record in database
            sta = self.env['droga.purchase.foregin.status'].create(status)

    @api.model
    def create(self, vals):
        # get sequence number for each company
        self_comp = self.with_company(self.company_id)
        vals['name'] = self_comp.env['ir.sequence'].next_by_code(
            'droga.purchase.request.rfq') or '/'
        res = super(Rfq, self_comp).create(vals)

        return res

    def pick_winner(self):
        # update all record to no
        partners = self.env['droga.purhcase.request.rfq.line'].search(
            [('rfq_id', '=', self.id)])

        for partner in partners:
            partner.write({'winner': 'No'})

        # get product list
        products = self.purhcase_request_id.purhcase_request_lines.product_id

        # pick winner for each product
        for product in products:
            # get suppliers
            suppliers = self.env['droga.purhcase.request.rfq.line'].search(
                [('rfq_id', '=', self.id), ('product_id', '=', product.id)])
            winner_supplier = {}
            # pick winner
            if suppliers.ids:
                winner_supplier = suppliers[0]

                for supplier in suppliers:
                    if supplier.total_price < winner_supplier.total_price:
                        winner_supplier = supplier

                if winner_supplier:
                    winner_supplier.write({'winner': 'Yes'})

            self.write({'state': 'Winner Picked'})

        return True

    def create_purchase_orders_automatically(self):
        # check if there is no purchase related with the rfq
        puchase_orders = self.env['purchase.order'].search(
            [('rfq_id', '=', self.id)])

        if puchase_orders.ids:
            raise UserError(
                _("Purchase order for the current Request for Quotation is created "))

        suppliers = []
        # get unique suppliers from the rfq
        for line in self.rfq_lines:
            if line.winner == "Yes" and self.check_supplier(line.supplier_name, suppliers) == 0:
                suppliers.append(line)

        if suppliers:
            for supplier in suppliers:
                vals = {
                    'name': 'New',
                            'state': 'draft',
                            'date_order': datetime.now(),
                            'rfq_id': supplier.rfq_id.id,
                            'partner_id': supplier.supplier_id.id
                }
                vals['order_line'] = []

                # get products the supplier won
                for line in self.rfq_lines:
                    if line.winner == "Yes" and line.supplier_id == supplier.supplier_id:

                        order_line_vals = (0, 0, {
                            'date_planned': fields.Date.today(),
                            'name': line.product_id.name,
                            'price_unit': line.unit_price,
                            'product_id': line.product_id.id,
                            'product_qty':  line.product_qty,
                            'product_uom': line.product_uom.id,
                            'taxes_id': [(6, 0, line.tax_id.ids)],
                        })

                        vals['order_line'].append(order_line_vals)

                # create purchase orders
                purchase_order = self.env['purchase.order'].create(vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Purchase Order Created Successfully',
                'type': 'success',
                'sticky': False
            }
        }

    def check_supplier(self, supplier_name, suppliers):
        count = 0
        for s in suppliers:
            if supplier_name == s.supplier_name:
                count += 1
        return count


class Rfq_Detail(models.Model):
    _name = 'droga.purhcase.request.rfq.line'
    _description = 'Request for Quotation Detail'
    _order = "supplier_name asc"

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")
    # related fields
    purhcase_request_id = fields.Many2one(related='rfq_id.purhcase_request_id')
    purhcase_request_lines = fields.One2many(
        related='purhcase_request_id.purhcase_request_lines')

    supplier_id = fields.Many2one('res.partner', string='Supplier')
    supplier_name = fields.Char(related="supplier_id.name", store=True)
    product_id = fields.Many2one('product.product', string='Product', domain=[
                                 ('purchase_ok', '=', True)], change_default=True)
    product_qty = fields.Float(
        string='Quantity', digits='Product Unit of Measure', required=True, default=1)
    unit_price = fields.Float('Unit Price', required=True)
    total_price = fields.Float(
        'Total Price', compute="_compute_total", store=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]", required=True)
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id')

    price_subtotal = fields.Float(
        compute='_compute_total', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_total',
                             string='Taxes', readonly=True, store=True)
    price_total = fields.Float(
        compute='_compute_total', string='Total', readonly=True, store=True)

    tax_id = fields.Many2many('account.tax', string='Taxes',
                              domain=['|', ('active', '=', False), ('active', '=', True)])

    winner = fields.Selection([('Yes', 'Yes'), ('No', 'No')], default="No")

    @api.depends('product_id', 'product_qty', 'unit_price', 'tax_id')
    def _compute_total(self):
        for record in self:
            price = record.unit_price
            taxes = record.tax_id.compute_all(
                price, record.rfq_id.currency_id, record.product_qty)

            record.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total_price': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.model
    def create(self, vals):
        if vals:
            if self.check_double_product_supplier_entry(vals) > 0:
                raise UserError(_("You can't enter duplicate data"))

        return super(Rfq_Detail, self).create(vals)

    @api.depends('product_qty', 'unit_price')
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.product_qty*record.unit_price

    @api.onchange('product_id')
    def onchange_product_id(self):
        x = self.purhcase_request_lines.product_id.ids
        # set quantity
        products = self.purhcase_request_lines

        for product in products:
            if product.product_id.id == self.product_id.id:
                self.product_qty = product.product_qty

        return {'domain': {'product_id': [('id', 'in', (x))]}}

    def check_double_product_supplier_entry(self, vals):
        if self:
            return self.env['droga.purhcase.request.rfq.line'].search_count(
                [('rfq_id', '=', self.rfq_id.id), ('supplier_id', '=', self.supplier_id.id), ('product_id', '=', self.product_id.id)])
        else:
            return self.env['droga.purhcase.request.rfq.line'].search_count(
                [('rfq_id', '=', vals['rfq_id']), ('supplier_id', '=', vals['supplier_id']), ('product_id', '=', vals['product_id'])])
