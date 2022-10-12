from math import fabs
from odoo import _, api, fields, models
from datetime import datetime


class purhcase_request(models.Model):
    _name = 'droga.purhcase.request'
    _description = 'Purhcase Request'
    _order = "name desc"

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    def _get_employee_id(self):
        # assigning the related employee of the logged in user
        employee_rec = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.id

    def _get_department_id(self):
        # assigning the related employee of the logged in user
        employee_rec = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        return employee_rec.department_id

    name = fields.Char('Request Reference', required=True,
                       index=True, copy=False, default='New')
    request_type = fields.Selection(
        [("Local", "Local"), ("Foregin", "Foregin")], default="Local")
    request_by = fields.Many2one(
        "hr.employee", string="Requested By", required=True, default=_get_employee_id)
    request_date = fields.Datetime(
        "Request Date", required=True, default=datetime.today())
    department = fields.Many2one(
        "hr.department", string="Department", required=True, default=_get_department_id)
    purpose = fields.Char("Purpose")
    purhcase_request_lines = fields.One2many(
        "droga.purhcase.request.line", "purhcase_request_id", required=True)

    state = fields.Selection(
        [("Draft", "Draft"), ("Submitted", "Submitted"), ("Verified", "Verified"), ("Budget Checked", "Budget Checked"), ("Approved", "Approved"), ("Cancel", "Canceled")], default="Draft", tracking=True)

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    approvals = fields.One2many(
        'studio.approval.entry', 'res_id', string='Approvals')

    buying_method = fields.Selection([("RFQ", "RFQ"), ("Bid", "Bid")])
    rfqs = fields.One2many('droga.purhcase.request.rfq',
                           'purhcase_request_id', string='RFQ')

    foregin_phase_rfqs = fields.One2many(
        "droga.purchase.foregin.status", "purchase_request_id_rfq_phase")

    # approvers
    department_manager = fields.Many2one(
        "hr.employee", compute="_get_manager_id")
    branch = fields.Many2one("account.analytic.account", string="Branch", domain=[
                             ('group_id', '=', 'Branch')])

    @api.depends("department")
    def _get_manager_id(self):
        for record in self:
            record.department_manager = record.department.manager_id

    @api.model
    def create(self, vals):
        # get sequence number for each company
        self_comp = self.with_company(self.company_id)
        vals['name'] = self_comp.env['ir.sequence'].next_by_code(
            'droga.purchase.request') or '/'
        res = super(purhcase_request, self_comp).create(vals)

        return res

    # submit request
    def submit_request(self):
        self.write({'state': 'Submitted'})
        return True

    # draft request
    def draft_request(self):
        self.write({'state': 'Draft'})
        return True

    # verify request
    def verify_request(self):
        self.write({'state': 'Verified'})
        return True

    # budget checked
    def budget_checked_request(self):
        self.write({'state': 'Budget Checked'})
        return True

    # approve request
    def approve_request(self):
        self.write({'state': 'Approved'})
        # load status steps
        # self.load_foregin_purchase_status()

        return True

    def open_rfq(self):
        view = self.env.ref(
            'droga_procurement.droga_purhcase_request_view_tree')

        return {
            'name': 'RFQ',
            'view_mode': 'tree,form',
            'res_model': 'droga.purhcase.request.rfq',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'res_id': self.id
        }

    def load_foregin_purchase_status(self):
        # get phase 1 or request for quotation steps
        rfq_steps = self.env["droga.foregin.purchase.phases"].search([])

        for rfq_step in rfq_steps:
            # create record in rfq step status one2manyobject
            status = {'purchase_request_id_rfq_phase': self.id,
                      'phase': rfq_step.id,
                      'status': 'Not Started'}
            # create the record in database
            sta = self.env['droga.purchase.foregin.status'].create(status)


class purhcase_request_line(models.Model):
    _name = "droga.purhcase.request.line"
    _description = "Purchase Request Line"

    purhcase_request_id = fields.Many2one("droga.purhcase.request")
    status=fields.Selection(
        [("Draft", "Draft"), ("Submitted", "Submitted"), ("Verified", "Verified"), ("Budget Checked", "Budget Checked"), ("Approved", "Approved"), ("Cancel", "Canceled")], default="Draft", tracking=True,related='purhcase_request_id.state')
    product_id = fields.Many2one('product.product', string='Product', domain=[
                                 ('purchase_ok', '=', True)], change_default=True)
    product_qty = fields.Float(
        string='Quantity', digits='Product Unit of Measure', required=True, default=1)

    unit_price = fields.Float('Unit Price')
    total_price = fields.Float(
        'Total Price', compute="_compute_total", store=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]", required=True)
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id')

    budget_product=fields.Boolean('Budget product?')
    expected_average_mon_cons=fields.Float('Expected average monthly consumption')      #Fix me, compute using product master
    current_stock_balance=fields.Float('Current balance')                               #Fix me, fetch from inventory
    selling_price_after_arrival=fields.Float('Arrival selling price')
    expected_margin=fields.Float('Expected margin')                     #Fix me, compute using sales price
    arrival_time=fields.Date('Arrival time')

    remark = fields.Char("Remark")

    @api.depends('product_qty', 'unit_price')
    def _compute_total(self):
        for record in self:
            record.total_price = record.unit_price*record.product_qty

    # set unit of measure
    @api.onchange('product_id')
    def set_unit(self):
        for record in self:
            record.product_uom = record.product_id.uom_id


class purchase_foregin_status(models.Model):
    _name = "droga.purchase.foregin.status"
    _description = "Status Tracking for Foregin Purchases"

    purchase_request_id_rfq_phase = fields.Many2one(
        "droga.purhcase.request", string="Purchase Request")

    rfq_id = fields.Many2one("droga.purhcase.request.rfq")

    phase = fields.Many2one("droga.foregin.purchase.phases")
    phase_name = fields.Selection(related="phase.phase_name", store=True)
    step = fields.Char(related="phase.step")
    status = fields.Selection(
        [("Not Started", "Not Started"), ("On Progress", "On Progress"),  ("Done", "Done")])
    done_date = fields.Date("Done Date")
    remark = fields.Char("Remark")
