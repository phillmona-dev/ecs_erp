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

    costc = fields.Many2one("account.analytic.account", string="Cost Center", domain=[
        ('plan_id', '=', 'Cost Center')])

    purpose = fields.Char("Purpose")

    pay_to = fields.Many2one("res.partner")

    approvals = fields.One2many(
        'studio.approval.entry', 'res_id', string='Approvals')

    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id)

    total_amount = fields.Float("Total Amount")
    exchange_rate = fields.Float("Exchange Rate", default=1)
    total_amount_etb = fields.Float(
        "Total Amount ETB", compute="_compute_total", required=True)
    amount_in_word = fields.Char(
        "Amount in Word", compute="_compute_amount_to_word")

    state = fields.Selection([('Draft', 'Draft'), ("Submitted", "Submitted"),
                              ('Approved', 'Approved'), ('Budget Approved', 'Budget Approved'),
                              ('Authorized', 'Authorized'), ('Cancelled', 'Cancelled')], default="Draft", tracking=True)
    paid_status = fields.Selection([('Not Paid', 'Not Paid'), ('Paid', 'Paid')], default="Not Paid")

    department_manager = fields.Many2one(
        "hr.employee", compute="_get_manager_id", store=True)
    department_manager_user_id = fields.Many2one(
        related="department_manager.user_id", store=True)

    # if the request is approved by department manager check this option
    approve_dept_manger = fields.Boolean("By Department", default=False,
                                         help="The request will be approved by the department manager")

    current_approver = fields.Many2one('hr.employee')
    budgetary_position = fields.Many2one("account.budget.post")
    budget_account = fields.Many2one("account.account")

    reject_message = fields.Char('Reason')

    approvals = fields.One2many(
        'studio.approval.entry', 'res_id', string='Approvals')

    budget_rem_balance = fields.Float("Remaining Balance", compute="_compute_budget_rem_balance")

    @api.model
    def create(self, vals):

        self.input_validation(vals)

        # get sequence number for each company
        self_comp = self.with_company(self.company_id)
        vals['name'] = self_comp.env['ir.sequence'].next_by_code(
            'droga.account.payment.request') or '/'
        res = super(PaymentRequest, self_comp).create(vals)

        return res

    def write(self, vals):

        self.input_validation(vals)
        res = super(PaymentRequest, self).write(vals)
        return res

    # compute total ETB amount
    @api.depends('total_amount', 'exchange_rate')
    def _compute_total(self):
        for record in self:
            record.total_amount_etb = record.total_amount * record.exchange_rate

    # @api.depends('total_amount', 'exchange_rate')
    def _compute_amount_to_word(self):
        for record in self:
            record.amount_in_word = str(self.convert_to_word(
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
        self.return_to_tree_view()

    def approve_request(self):
        self.write({'state': 'Approved'})
        # set activity done
        self.set_activity_done()
        # create new activity
        # get budget accountant
        users = self.get_users_for_roles('Business Control Specialist', self.company_id.id)
        for user in users:
            self.create_activity(user)

        self.return_to_tree_view()
        return True

    def budget_approve_request(self):
        self.input_validation('validation')
        self.write({'state': 'Budget Approved'})
        self.record_commitment_budget()
        self.set_activity_done()
        # create new activity
        # get budget accountant
        users = self.get_users_for_roles('Finance Operation Manager', self.company_id.id)
        for user in users:
            self.create_activity(user)
        self.return_to_tree_view()
        return True

    def authorize_request(self):
        self.write({'state': 'Authorized'})
        self.set_activity_done()
        self.return_to_tree_view()
        return True

    def reject_request(self):
        self.write({'state': 'Draft'})
        self.set_activity_done()
        self.create_reject_activity()
        self.return_to_tree_view()
        return True

    def cancel_request(self):
        self.write({'state': 'Cancelled'})
        self.cancel_commitment_budget()
        self.set_activity_done()
        self.return_to_tree_view()
        return True

    def set_paid_status(self):
        if self.paid_status == "Not Paid":
            self.write({'paid_status': 'Paid'})
        else:
            self.write({'paid_status': 'Not Paid'})

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

    def get_users_for_roles(self, role, company_id):
        users = []
        roles = self.env['res.groups'].search([('name', '=', role)])

        for user in roles.users:
            if user.company_id.id == company_id:
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

    def input_validation(self, vals):
        if 'total_amount' in vals:
            if vals['total_amount'] <= 0:
                raise ValidationError("Amount can't be zero or less than zero")

        # if self.state == 'Approved':
        # not self.budgetary_position or not self.budget_account:
        # raise ValidationError("Budget category and account must be filled")

    def record_commitment_budget(self):
        # record commitment budget when the budget approves
        for record in self:
            if record.state == "Budget Approved":
                # total purchase amount
                # create commitment record
                commitment_budget = {
                    'document_type': 'PMR',
                    'payment_request_id': record.id,
                    'purchase_request_total_amount': record.total_amount_etb,
                    'budget_date': record.request_date,
                    'budgetary_position': record.budgetary_position.id,
                    'expense_account': record.budget_account.id,
                    'analytic_account_id': record.costc.id,
                    'company_id': record.company_id.id,
                    'state': 'Active'
                }

                # persist to database
                self.env['droga.budget.commitment.budget'].create(
                    commitment_budget)

    @api.onchange('budgetary_position', 'budget_account')
    def _load_budgetary_position_accounts(self):
        for record in self:
            accounts = record.budgetary_position.account_ids.ids
            return {'domain': {'budget_account': [('id', 'in', (accounts))]}}

    def cancel_commitment_budget(self):
        records = self.env['droga.budget.commitment.budget'].search(
            [('payment_request_id', '=', self.id), ('state', '=', 'Active')])
        for record in records:
            record.write({'state': 'Closed'})

    def return_to_tree_view(self):
        view = self.env.ref('droga_finance.droga_account_payment_request_view_tree')
        return {
            'name': _('test'),
            'view_mode': 'tree',
            'view_id': view.id,
            'res_model': 'droga.account.payment.request',
            'context': {},
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def convert_to_word(self, number):
        number = str(number)
        int_side = number
        dec_side = ''
        for i in range(0, len(number)):
            if number[i] == '.':
                int_side = number[:i]
                dec_side = number[i + 1:]
                break
        while not (int_side.isdigit()) or not (dec_side.isdigit()) and dec_side != '':
            dec_side = ''
            # print('Only numbers are allowed! (decimals included, but not fractions)')
            int_side = number
            for i in range(0, len(number)):
                if number[i] == '.':
                    int_side = number[:i]
                    dec_side = number[i + 1:]
            user_choice = input()
        int_length = len(int_side)
        ones = ['', 'one ', 'two ', 'three ', 'four ', 'five ', 'six ', 'seven ', 'eight ', 'nine ']
        teens = ['ten ', 'eleven ', 'twelve ', 'thirteen ', 'fourteen ', 'fifteen ', 'sixteen ', 'seventeen ',
                 'eighteen ',
                 'nineteen ']
        decades = ['', '', 'twenty ', 'thirty ', 'forty ', 'fifty ', 'sixty ', 'seventy ', 'eighty ', 'ninety ']
        hundreds = ['', 'one hundred ', 'two hundred ', 'three hundred ', 'four hundred ', 'five hundred ',
                    'six hundred ',
                    'seven hundred ', 'eight hundred ', 'nine hundred ']
        comma = ['thousand ', 'million ', 'trillion ', 'quadrillion ']
        word = ''
        int_length = len(int_side)
        dec_length = len(dec_side)
        change = int_length
        up_change = 0
        while change > 0:
            if int_side == '':
                break
            if number == '0':
                word = 'zero'
                break
            elif change > 1 and int_side[change - 2] == '1':
                for i in range(0, 10):
                    if int_side[change - 1] == str(i):
                        word = teens[i] + word
            else:
                if change > 0:
                    for i in range(0, 10):
                        if int_side[change - 1] == str(i):
                            word = ones[i] + word
                if change > 1:
                    for i in range(0, 10):
                        if int_side[change - 2] == str(i):
                            word = decades[i] + word
            if change > 2:
                for i in range(0, 10):
                    if int_side[change - 3] == str(i):
                        word = hundreds[i] + word
            if change > 3:
                word = comma[up_change] + word
            change -= 3
            up_change += 1
        # word += 'birr '

        print(dec_side)
        """
        for i in range(0, len(dec_side)):
            for x in range(0, 10):
                if dec_side[i] == str(x):
                    word += ones[x]"""

        if dec_side not in ['', '0', '00']:
            word += 'birr and '
            word += self.convert_to_word(dec_side) + " cents"

        word += " only"

        return word.title()

    def _compute_budget_rem_balance(self):
        now = datetime.today().date()

        if now.month >= 7 and now.day >= 7:
            date_from = datetime(now.year, 7, 8)
            date_to = datetime(now.year + 1, 7, 7)
        else:
            date_from = datetime(now.year - 1, 7, 8)
            date_to = datetime(now.year, 7, 7)

        for record in self:
            record.budget_rem_balance = 0
            # get budget from remaining budget
            if record.budgetary_position.id and record.costc.id and record.budget_account.id:
                self.env.cr.execute("""select distinct b.account,a.general_budget_id,a.analytic_account_id,sum(b.remaining_balance) as remaining_balance from crossovered_budget_lines a 
            inner join crossovered_budget_lines_detail b on a.id=b.budgetary_position_id 
            where a.general_budget_id=%s and a.analytic_account_id=%s and b.account=%s and (a.date_from>=%s and a.date_to<=%s)
            group by b.account,a.general_budget_id,a.analytic_account_id """, (
                    record.budgetary_position.id, record.costc.id, record.budget_account.id,
                    date_from, date_to))
                res = self.env.cr.dictfetchone()

                # update remaining balance
                if res != None:
                    record.budget_rem_balance = res['remaining_balance']
