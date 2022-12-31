from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class PaymentRequest(models.Model):
    _name = 'droga.account.payment.request'
    _description = 'Payment Request Form'

    _order = 'name desc'

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

    def get_current_user_id(self):
        context = self._context
        return context.get('uid')

    def identify_requester(self):
        context = self._context

        if context.get('uid') == self.create_uid.id:
            self.requester = True
        else:
            self.requester = False

    # for approvers
    logged_user_id = fields.Many2one('res.users', default=get_current_user_id)
    requester = fields.Boolean('Requester', default=False, compute='identify_requester')

    name = fields.Char("Request Number", default='New')
    purchase_order_id = fields.Many2one("purchase.order")
    payment_type = fields.Selection(
        [('Normal', 'Normal'), ('Urgent', 'Urgent'), ('Withoutpo', 'Withoutpo')])
    request_by = fields.Many2one(
        "hr.employee", string="Requested By", required=True, default=_get_employee_id)
    request_date = fields.Datetime(
        "Request Date", required=True, default=datetime.today())
    payment_due_date = fields.Datetime("Payment Due Date")
    department = fields.Many2one(
        "hr.department", string="Department", required=True, default=_get_department_id)

    purpose = fields.Char("Purpose")

    pay_to = fields.Many2one("res.partner")

    approvals = fields.One2many(
        'studio.approval.entry', 'res_id', string='Approvals')

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.ref('base.main_company').currency_id)

    total_amount = fields.Float("Total Amount")
    exchange_rate = fields.Float("Exchange Rate", default=1)
    total_amount_etb = fields.Float(
        "Total Amount ETB", compute="_compute_total", required=True)
    amount_in_word = fields.Char(
        "Amount in Word", compute="_compute_amount_to_word", store=True)

    state = fields.Selection([('Draft', 'Draft'), ("Submitted", "Submitted"),
                              ('Approved', 'Approved'), ('Budget Approved', 'Budget Approved'),
                              ('Authorized', 'Authorized'), ('Cancelled', 'Cancelled')], default="Draft", tracking=True)

    department_manager = fields.Many2one(
        "hr.employee", compute="_get_manager_id", store=True)
    department_manager_user_id = fields.Many2one(
        related="department_manager.user_id", store=True)

    # if the request is approved by department manager check this option
    approve_dept_manger = fields.Boolean("By Department Manager", default=False)

    current_approver = fields.Many2one('hr.employee')

    reject_message = fields.Char('Reason')

    @api.model
    def create(self, vals):
        # get sequence number for each company
        self_comp = self.with_company(self.company_id)
        vals['name'] = self_comp.env['ir.sequence'].next_by_code(
            'droga.account.payment.request') or '/'
        res = super(PaymentRequest, self_comp).create(vals)

        return res

    # compute total ETB amount
    @api.depends('total_amount', 'exchange_rate')
    def _compute_total(self):
        self.total_amount_etb = self.total_amount * self.exchange_rate

    @api.depends('total_amount', 'exchange_rate')
    def _compute_amount_to_word(self):
        for record in self:
            record.amount_in_word = str(record.currency_id.amount_to_text(
                record.total_amount * record.exchange_rate))

    def submit_request(self):
        self.write({'state': 'Submitted', 'reject_message': ''})
        # check for requester manager
        self.set_activity_done()
        self._get_manager_id()

        if not self.department_manager:
            raise ValidationError(
                "A manager is not set for the requester or the department, please contact HR to set manager for your employee record")

        # create activity for the approver
        self.create_activity(self.department_manager_user_id.id)
        return True

    def approve_request(self):
        self.write({'state': 'Approved'})
        # set activity done
        self.set_activity_done()
        # create new activity
        # get budget accountant
        users = self.get_users_for_roles('Business Control Specialist')
        for user in users:
            self.create_activity(user)
        return True

    def budget_approve_request(self):
        self.write({'state': 'Budget Approved'})
        self.set_activity_done()
        # create new activity
        # get budget accountant
        users = self.get_users_for_roles('Finance Operation Manager')
        for user in users:
            self.create_activity(user)
        return True

    def authorize_request(self):
        self.write({'state': 'Authorized'})
        self.set_activity_done()
        return True

    def reject_request(self):
        self.write({'state': 'Draft'})
        self.set_activity_done()
        self.create_reject_activity()
        return True

    def cancel_request(self):
        self.write({'state': 'Cancelled'})
        self.set_activity_done()
        return True

    def set_activity_done(self):
        activity = self.env["mail.activity"].search(
            [('res_name', '=', self.name)])
        if activity:
            activity.sudo().action_done()

    def create_activity(self, user_id):
        # create mail activity for the approval
        todos = dict(res_id=self.id,
                     res_model_id=self.env['ir.model'].search([('model', '=', 'droga.account.payment.request')]).id,
                     user_id=user_id, summary='Grant Approval', note='You have a request to approve',
                     activity_type_id=4,
                     date_deadline=datetime.now())

        self.env['mail.activity'].sudo().create(todos)

    def create_reject_activity(self):
        # create mail activity for the approval

        todos = dict(res_id=self.id,
                     res_model_id=self.env['ir.model'].search([('model', '=', 'droga.account.payment.request')]).id,
                     user_id=self.create_uid.id, summary='Request Rejected', note=self.reject_message,
                     activity_type_id=4,
                     date_deadline=datetime.now())

        self.env['mail.activity'].sudo().create(todos)

    @api.depends("department")
    def _get_manager_id(self):
        for record in self:
            if record.approve_dept_manger:
                record.department_manager = record.department.manager_id
            else:
                record.department_manager = record.request_by.parent_id

    def get_users_for_roles(self, role):
        users = []
        roles = self.env['res.groups'].search([('name', '=', role)])

        for user in roles.users:
            users.append(user.id)
        return users

    def reject_box(self):
        view = self.env.ref(
            'droga_finance.droga_account_payment_request_reject_view_form')

        return {
            'name': 'Reject',
            'view_mode': 'form',
            'res_model': 'droga.account.payment.request',
            'view_id': view.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': self.id
        }
