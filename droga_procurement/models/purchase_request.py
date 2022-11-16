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

    purhcase_request_lines_expectetd = fields.One2many(
        "droga.purhcase.request.line", "purhcase_request_id", required=True)

    purhcase_request_lines_market_analysis = fields.One2many(
        "droga.purhcase.request.line", "purhcase_request_id", required=True)

    purhcase_request_lines_foregin_supp_list = fields.One2many(
        "droga.purhcase.request.line", "purhcase_request_id", required=True)

    purhcase_request_lines_foregin_competitors = fields.One2many(
        "droga.purhcase.request.line", "purhcase_request_id", required=True)

    purchase_analysis_report = fields.One2many(
        "droga.purhcase.request.line", "purhcase_request_id")

    state = fields.Selection(
        [("Draft", "Draft"), ("Submitted", "Submitted"), ("Verified", "Verified"), ("Budget Approved", "Budget Approved"), ("Approved", "Approved"), ("Cancel", "Canceled")], default="Draft", tracking=True)

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True, default=lambda self: self.env.ref('base.main_company').currency_id)

    exchange_rate = fields.Float(
        "Exchange Rate", required=True, default=1.00, digits=(12, 4))

    approvals = fields.One2many(
        'studio.approval.entry', 'res_id', string='Approvals')

    buying_method = fields.Selection([("RFQ", "RFQ"), ("Bid", "Bid")])
    rfqs = fields.One2many('droga.purhcase.request.rfq',
                           'purhcase_request_id', string='RFQ')

    foregin_phase_rfqs = fields.One2many(
        "droga.purchase.foregin.status", "purchase_request_id_rfq_phase")

    # approvers
    department_manager = fields.Many2one(
        "hr.employee", compute="_get_manager_id", store=True)
    department_manager_user_id = fields.Many2one(
        related="department_manager.user_id", store=True)

    branch = fields.Many2one("account.analytic.account", string="Cost Center", domain=[
                             ('plan_id', '=', 'Profit Center')])

    @api.depends("department")
    def _get_manager_id(self):
        for record in self:
            record.department_manager = record.department.manager_id

    @api.model
    def create(self, vals):
        # get sequence number for each company
        company_id = vals.get('company_id', self.default_get(
            ['company_id'])['company_id'])

        self_comp = self.with_company(company_id)

        if vals['request_type'] == 'Local':
            vals['name'] = self_comp.env['ir.sequence'].next_by_code(
                'droga.purchase.request.local') or '/'
        else:
            vals['name'] = self_comp.env['ir.sequence'].next_by_code(
                'droga.purchase.request.foreign') or '/'

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
        # mark activity as done
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.name)])
        if activity:
            activity.action_feedback()
        return True

    # rejet request
    def reject_request(self):
        self.write({'state': 'Draft'})
        return True

    def cancel_request(self):
        self.write({'state': 'Cancel'})
        return True

    # budget checked
    def budget_checked_request(self):
        # check for budgetary position and expense account
        for record in self.purhcase_request_lines:
            if not record.budgetary_position.ids or not record.expense_account.ids:
                return {
                    'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': 'Budget category or expense account can''t be empty',
                                'type': 'danger',
                                'sticky': False
                            }
                }

        self.write({'state': 'Budget Approved'})
        return True

    # approve request
    def approve_request(self):
        self.write({'state': 'Approved'})
        # record commitment budget
        self.record_commitment_budget()

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

    def record_commitment_budget(self):
        # record commitement budget when the budget approves
        for record in self:
            if record.state == "Approved":
                # total purchase amount
                lines_include_in_total = []
                for line in record.purhcase_request_lines:

                    # create commitment record
                    commitment_budget = {
                        'document_type': 'PR',
                        'purchase_request_id': record.id,
                        'purchase_request_total_amount': line.total_price,
                        'budget_date': record.request_date,
                        'budgetary_position': line.budgetary_position.id,
                        'expense_account': line.expense_account.id,
                        'analytic_account_id': self.branch.id,
                        'company_id': record.company_id.id,
                        'state': 'Active'
                    }

                    # persist to database
                    self.env['droga.budget.commitment.budget'].create(
                        commitment_budget)


class purhcase_request_line(models.Model):
    _name = "droga.purhcase.request.line"
    _description = "Purchase Request Line"

    purhcase_request_id = fields.Many2one("droga.purhcase.request")
    exchange_rate = fields.Float(
        related="purhcase_request_id.exchange_rate", store=True)
    company_id = fields.Many2one(
        'res.company', related='purhcase_request_id.company_id', string='Company', store=True, readonly=True)
    status = fields.Selection(
        [("Draft", "Draft"), ("Submitted", "Submitted"), ("Verified", "Verified"), ("Budget Checked", "Budget Checked"), ("Approved", "Approved"), ("Cancel", "Canceled")], default="Draft", tracking=True, related='purhcase_request_id.state')
    product_id = fields.Many2one('product.product', string='Product', domain=[
                                 ('purchase_ok', '=', True)], change_default=True)
    product_qty = fields.Float(
        string='Quantity', digits='Product Unit of Measure', required=True, default=1)

    unit_price = fields.Float('Unit Price')
    total_price = fields.Float(
        'Total Price', compute="_compute_total", store=True)

    unit_price_foregin = fields.Float('Unit Price')
    total_price_foregin = fields.Float(
        'Total Price', compute="_compute_total", store=True)

    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]", required=True)
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id')

    budget_product = fields.Boolean('Budget product?')
    expected_average_mon_cons = fields.Float(
        'Expected average monthly consumption')  # Fix me, compute using product master
    current_stock_balance = fields.Float(
        'Current balance')  # Fix me, fetch from inventory
    selling_price_after_arrival = fields.Float('Arrival selling price')
    # Fix me, compute using sales price
    expected_margin = fields.Float('Expected margin')
    arrival_time = fields.Date('Arrival time')

    budgetary_position = fields.Many2one("account.budget.post")
    expense_account = fields.Many2one("account.account")

    remark = fields.Char("Remark")

    # field for anlysis report
    four_month_order_qty = fields.Float(
        "Four Month Qty", compute="_consumption_total", help="Order Quantity times Average Monthly Consumption", store=True)
    six_month_order_qty = fields.Float(
        "Six Month Qty", compute="_consumption_total", help="Order Quantity times Average Monthly Consumption", store=True)

    order_qty_and_current_stcok = fields.Float(
        "Order Qty & Current Stock", compute="_consumption_total", help="Order Quantity Plus Current Stock", store=True)

    @api.depends('product_qty', 'unit_price', 'unit_price_foregin', 'exchange_rate')
    def _compute_total(self):
        for record in self:
            if record.purhcase_request_id.request_type == 'Local':
                record.total_price = record.unit_price*record.product_qty
            else:
                record.unit_price = record.unit_price_foregin*record.exchange_rate
                record.total_price = record.unit_price*record.product_qty
                record.total_price_foregin = record.unit_price_foregin*record.product_qty

    # set unit of measure
    @api.onchange('product_id')
    def set_unit(self):
        for record in self:
            record.product_uom = record.product_id.uom_id

    @api.onchange('budgetary_position', 'expense_account')
    def _load_budgetary_position_accounts(self):
        accounts = self.budgetary_position.account_ids.ids
        return {'domain': {'expense_account': [('id', 'in', (accounts))]}}

    @api.depends('product_qty', 'expected_average_mon_cons', 'current_stock_balance')
    def _consumption_total(self):
        for record in self:
            record.four_month_order_qty = record.expected_average_mon_cons*4
            record.six_month_order_qty = record.expected_average_mon_cons*6
            record.order_qty_and_current_stcok = record.product_qty + \
                record.current_stock_balance
        return True


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
