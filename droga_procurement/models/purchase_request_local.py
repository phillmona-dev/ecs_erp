from math import fabs
from odoo import _, api, fields, models
from datetime import datetime


class purchase_request_local(models.Model):
    _name = 'droga.purchase.request.local'
    _description = 'Purchase Request'
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

    # compute total purchase amount
    @api.depends('purchase_request_lines.total_price')
    def compute_total_purchase_amount(self):
        total = 0
        for record in self.purchase_request_lines:
            total += record.total_price

        self.total_amount = total

    def get_current_uid(self):
        for record in self:
            if self.env.context.get('uid', False):
                record.current_uid = self.env.context.get('uid', False)
            else:
                record.current_uid = False

            if record.department_manager_user_id == record.current_uid:
                record.is_department_manager = True
            else:
                record.is_department_manager = False

    current_uid = fields.Integer(compute='get_current_uid')
    is_department_manager = fields.Boolean(compute='get_current_uid')

    name = fields.Char('Request Reference', required=True,
                       index=True, copy=False, default='New')
    request_type = fields.Selection(
        [("Local", "Local"), ("Foreign", "Foregin")], default="Local")
    purchase_type = fields.Selection([('product', 'Goods'), ('service', 'Service')],
                                     default="product")
    request_by = fields.Many2one(
        "hr.employee", string="Requested By", required=True, default=_get_employee_id)
    request_date = fields.Datetime(
        "Request Date", required=True, default=datetime.today())
    department = fields.Many2one(
        "hr.department", string="Department", required=True, default=_get_department_id)
    purpose = fields.Char("Purpose")

    purchase_request_lines = fields.One2many(
        "droga.purchase.request.line.local", "purchase_request_id", required=True)

    state = fields.Selection(
        [("Draft", "Draft"), ("Submitted", "Submitted"), ("Verified", "Verified"),
         ("Budget Approved", "Budget Approved"), ("Procurement Manager", "PR Manager Approved"),
         ("Approved", "Ceo Approved"), ("Cancel", "Canceled")], default="Draft", tracking=True)

    wf_state = fields.Selection(
        [('On Progress', 'On Progress'), ('Approved', 'Approved')], default="On Progress")

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id)

    exchange_rate = fields.Float(
        "Exchange Rate", required=True, default=1.00, digits=(12, 4))

    approvals = fields.One2many(
        'studio.approval.entry', 'res_id', string='Approvals')

    buying_method = fields.Selection([("RFQ", "RFQ"), ("Bid", "Bid")])
    # rfqs = fields.One2many('droga.purchase.request.rfq.local', 'purchase_request_id', string='RFQ')

    # approvers
    department_manager = fields.Many2one(
        "hr.employee", compute="_get_manager_id", store=True)
    department_manager_user_id = fields.Many2one(
        related="department_manager.user_id", store=True)

    branch = fields.Many2one("account.analytic.account", string="Cost Center", domain=[
        ('plan_id', '=', 'Cost Center')])

    total_amount = fields.Float(
        "Total Amount", compute="compute_total_purchase_amount", store=True)

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

        res = super(purchase_request_local, self_comp).create(vals)

        return res

    def write(self, vals):

        res = super(purchase_request_local, self).write(vals)
        # calculate total purchase price

        return res

    # submit request
    def submit_request(self):
        if len(self.purchase_request_lines) == 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'At least one product must be requested to submit the request.',
                    'type': 'danger',
                    'sticky': False
                }
            }

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

    # reject request
    def reject_request(self):
        self.write({'state': 'Draft'})
        return True

    def cancel_request(self):
        self.write({'state': 'Cancel'})
        self.cancel_commitment_budget()
        return True

    # budget checked
    def budget_checked_request(self):
        # check for budgetary position and expense account
        for record in self.purchase_request_lines:
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
        self.record_commitment_budget()
        return True

    def approve_request_pr_manager(self):
        self.write({'state': 'Procurement Manager'})
        if self.total_amount <= 100000:
            self.write({'wf_state': 'Approved'})
        return True

    # approve request
    def approve_request(self):
        self.write({'state': 'Approved'})
        self.write({'wf_state': 'Approved'})
        # record commitment budget
        return True

    def open_rfq(self):
        view = self.env.ref(
            'droga_procurement.droga_purchase_request_rfq_local_view_tree')

        return {
            'name': 'RFQ',
            'view_mode': 'tree,form',
            'res_model': 'droga.purchase.request.rfq.local',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'res_id': self.id
        }

    def record_commitment_budget(self):
        # record commitement budget when the budget approves
        for record in self:
            if record.state == "Budget Approved":
                # total purchase amount
                lines_include_in_total = []
                for line in record.purchase_request_lines:
                    # create commitment record
                    commitment_budget = {
                        'document_type': 'PR',
                        'purchase_request_local_id': record.id,
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

    def cancel_commitment_budget(self):
        records = self.env['droga.budget.commitment.budget'].search(
            [('purchase_request_id', '=', self.id), ('state', '=', 'Active')])
        for record in records:
            record.write({'state': 'Closed'})


class purchase_request_line_local(models.Model):
    _name = "droga.purchase.request.line.local"
    _description = "Purchase Request Line"

    purchase_request_id = fields.Many2one("droga.purchase.request.local")

    company_id = fields.Many2one(
        'res.company', related='purchase_request_id.company_id', string='Company', store=True, readonly=True)
    status = fields.Selection(related='purchase_request_id.state')
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)],
                                 change_default=True)
    product_qty = fields.Float(
        string='Quantity', digits='Product Unit of Measure', required=True, default=1)

    unit_price = fields.Float('Unit Price')
    total_price = fields.Float(
        'Total Price', compute="_compute_total", store=True)

    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  domain="[('category_id', '=', product_uom_category_id)]", required=True)
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id')

    budgetary_position = fields.Many2one("account.budget.post")
    expense_account = fields.Many2one("account.account")

    remaining_budget = fields.Float(
        "Remaining Budget", compute="_get_remaining_budget", store=True)

    remark = fields.Char("Remark")

    @api.depends('product_qty', 'unit_price')
    def _compute_total(self):
        for record in self:
            record.total_price = record.unit_price * record.product_qty

    # set unit of measure
    @api.onchange('product_id')
    def set_unit_product(self):
        for record in self:
            record.product_uom = record.product_id.uom_id
            # get product type

            product_type = record.purchase_request_id.purchase_type
            return {'domain': {'product_id': [('detailed_type', '=', product_type)]}}

    @api.onchange('budgetary_position', 'expense_account')
    def _load_budgetary_position_accounts(self):
        for record in self:
            accounts = record.budgetary_position.account_ids.ids
            return {'domain': {'expense_account': [('id', 'in', (accounts))]}}

    @api.depends('budgetary_position', 'expense_account')
    def _get_remaining_budget(self):

        now = datetime.today().date()

        if now.month >= 7 and now.day >= 7:
            date_from = datetime(now.year, 7, 8)
            date_to = datetime(now.year + 1, 7, 7)
        else:
            date_from = datetime(now.year - 1, 7, 8)
            date_to = datetime(now.year, 7, 7)

        for record in self:
            # get budget from remaining budget
            if record.budgetary_position.id and record.purchase_request_id.branch.id and record.expense_account.id:
                self.env.cr.execute("""select distinct b.account,a.general_budget_id,a.analytic_account_id,sum(b.remaining_balance) as remaining_balance from crossovered_budget_lines a 
    inner join crossovered_budget_lines_detail b on a.id=b.budgetary_position_id 
    where a.general_budget_id=%s and a.analytic_account_id=%s and b.account=%s and (a.date_from>=%s and a.date_to<=%s)
    group by b.account,a.general_budget_id,a.analytic_account_id """, (
                    record.budgetary_position.id, record.purchase_request_id.branch.id, record.expense_account.id,
                    date_from, date_to))
                res = self.env.cr.dictfetchone()

                # update remaining balance
                if res != None:
                    record.remaining_budget = res['remaining_balance']
