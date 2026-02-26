from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND


class CrossoveredBudget(models.Model):
    _name = "crossovered.budget"
    _description = "Budget"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Budget Name", required=True)
    user_id = fields.Many2one("res.users", "Responsible", default=lambda self: self.env.user)
    date_from = fields.Date("Start Date", required=True)
    date_to = fields.Date("End Date", required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("confirm", "Confirmed"),
            ("validate", "Validated"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
        index=True,
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )
    crossovered_budget_line = fields.One2many(
        "crossovered.budget.lines",
        "crossovered_budget_id",
        string="Budget Lines",
        copy=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    fiscal_year = fields.Many2one("account.fiscal.year")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_("Budget end date may not be before the starting date."))

    def action_budget_confirm(self):
        self.write({"state": "confirm"})

    def action_budget_draft(self):
        self.write({"state": "draft"})

    def action_budget_validate(self):
        self.write({"state": "validate"})

    def action_budget_cancel(self):
        self.write({"state": "cancel"})

    def action_budget_done(self):
        self.write({"state": "done"})

    def unlink(self):
        for record in self:
            has_values = any(
                line.planned_amount or line.reallaocation_addition or line.addition
                for line in record.crossovered_budget_line
            )
            if has_values and record.state != "cancel":
                raise ValidationError(_("You can't delete budget record, it contains budget data."))
        return super().unlink()

    @api.onchange("fiscal_year")
    def _on_change_fiscal_year(self):
        for record in self.filtered("fiscal_year"):
            record.date_from = record.fiscal_year.date_from
            record.date_to = record.fiscal_year.date_to


class CrossoveredBudgetLines(models.Model):
    _name = "crossovered.budget.lines"
    _description = "Budget Line"

    name = fields.Char(compute="_compute_line_name")
    crossovered_budget_id = fields.Many2one(
        "crossovered.budget",
        string="Budget",
        ondelete="cascade",
        index=True,
        required=True,
    )
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account")
    general_budget_id = fields.Many2one("account.budget.post", string="Budgetary Position")
    date_from = fields.Date("Start Date", required=True)
    date_to = fields.Date("End Date", required=True)
    paid_date = fields.Date("Paid Date")
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    planned_amount = fields.Monetary(
        "Planned Amount",
        required=True,
        default=0.0,
        help="Amount you plan to earn/spend.",
    )
    practical_amount = fields.Monetary(compute="_compute_practical_amount", string="Practical Amount")
    theoritical_amount = fields.Monetary(compute="_compute_theoritical_amount", string="Theoretical Amount")
    percentage = fields.Float(compute="_compute_percentage", string="Achievement")
    company_id = fields.Many2one(
        related="crossovered_budget_id.company_id",
        comodel_name="res.company",
        string="Company",
        store=True,
        readonly=True,
    )
    is_above_budget = fields.Boolean(compute="_compute_is_above_budget")
    crossovered_budget_state = fields.Selection(
        related="crossovered_budget_id.state",
        string="Budget State",
        store=True,
        readonly=True,
    )

    fiscal_year = fields.Many2one(related="crossovered_budget_id.fiscal_year")
    period = fields.Many2one(
        "account.fiscal.year.period",
        required=True,
        domain="[('fiscal_year_id', '=', fiscal_year)]",
    )
    commitment_budget = fields.Float("Commitment")
    remaining_balance = fields.Float("Remaining")
    reallaocation_addition = fields.Float("Reallocation +")
    reallaocation_deduction = fields.Float("Reallocation -")
    addition = fields.Float("Addition")
    revised_budget = fields.Float("Revised")
    budget_line_details = fields.One2many(
        "crossovered.budget.lines.detail",
        "budgetary_position_id",
    )

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        fields_list = {"practical_amount", "theoritical_amount", "percentage"}

        def truncate_aggr(field_name):
            field_no_aggr = field_name.split(":", 1)[0]
            if field_no_aggr in fields_list:
                return field_no_aggr
            return field_name

        fields = {truncate_aggr(field_name) for field_name in fields}
        result = super().read_group(
            domain,
            list(fields - fields_list),
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

        if fields & fields_list:
            for group_line in result:
                if "practical_amount" in fields:
                    group_line["practical_amount"] = 0
                if "theoritical_amount" in fields:
                    group_line["theoritical_amount"] = 0
                if "percentage" in fields:
                    group_line["percentage"] = 0
                    group_line["practical_amount"] = 0
                    group_line["theoritical_amount"] = 0

                group_domain = group_line.get("__domain") or domain
                for budget_line in self.search(group_domain):
                    if "practical_amount" in fields or "percentage" in fields:
                        group_line["practical_amount"] += budget_line.practical_amount
                    if "theoritical_amount" in fields or "percentage" in fields:
                        group_line["theoritical_amount"] += budget_line.theoritical_amount
                    if "percentage" in fields and group_line["theoritical_amount"]:
                        group_line["percentage"] = float(
                            (group_line["practical_amount"] or 0.0) / group_line["theoritical_amount"]
                        )
        return result

    @api.depends("crossovered_budget_id", "general_budget_id", "analytic_account_id")
    def _compute_line_name(self):
        for record in self:
            computed_name = record.crossovered_budget_id.name or ""
            if record.general_budget_id:
                computed_name = f"{computed_name} - {record.general_budget_id.name}"
            if record.analytic_account_id:
                computed_name = f"{computed_name} - {record.analytic_account_id.name}"
            record.name = computed_name

    @api.depends(
        "date_from",
        "date_to",
        "general_budget_id",
        "general_budget_id.account_ids",
        "analytic_account_id",
    )
    def _compute_practical_amount(self):
        analytic_line = self.env["account.analytic.line"]
        move_line = self.env["account.move.line"]
        for line in self:
            line.practical_amount = 0.0
            if not line.date_from or not line.date_to or not line.company_id:
                continue

            if line.analytic_account_id:
                domain = [
                    ("account_id", "=", line.analytic_account_id.id),
                    ("date", ">=", line.date_from),
                    ("date", "<=", line.date_to),
                    ("company_id", "=", line.company_id.id),
                ]
                if line.general_budget_id.account_ids:
                    domain.append(("general_account_id", "in", line.general_budget_id.account_ids.ids))
                line.practical_amount = sum(analytic_line.search(domain).mapped("amount"))
            elif line.general_budget_id.account_ids:
                domain = [
                    ("company_id", "=", line.company_id.id),
                    ("date", ">=", line.date_from),
                    ("date", "<=", line.date_to),
                    ("parent_state", "=", "posted"),
                    ("account_id", "in", line.general_budget_id.account_ids.ids),
                ]
                line.practical_amount = -sum(move_line.search(domain).mapped("balance"))

    @api.depends("date_from", "date_to", "paid_date", "planned_amount")
    def _compute_theoritical_amount(self):
        today = fields.Date.today()
        for line in self:
            if not line.date_from or not line.date_to:
                line.theoritical_amount = 0.0
                continue

            if line.paid_date:
                line.theoritical_amount = 0.0 if today <= line.paid_date else line.planned_amount
                continue

            line_timedelta = line.date_to - line.date_from + timedelta(days=1)
            elapsed_timedelta = today - line.date_from + timedelta(days=1)

            if elapsed_timedelta.days < 0:
                line.theoritical_amount = 0.0
            elif line_timedelta.days > 0 and today < line.date_to:
                line.theoritical_amount = (
                    elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()
                ) * line.planned_amount
            else:
                line.theoritical_amount = line.planned_amount

    @api.depends("practical_amount", "theoritical_amount")
    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount:
                line.percentage = float((line.practical_amount or 0.0) / line.theoritical_amount)
            else:
                line.percentage = 0.0

    @api.depends("practical_amount", "theoritical_amount")
    def _compute_is_above_budget(self):
        for line in self:
            if line.theoritical_amount >= 0:
                line.is_above_budget = line.practical_amount > line.theoritical_amount
            else:
                line.is_above_budget = line.practical_amount < line.theoritical_amount

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        domain_list = []
        if self.date_from:
            domain_list.append(["|", ("date_from", "<=", self.date_from), ("date_from", "=", False)])
        if self.date_to:
            domain_list.append(["|", ("date_to", ">=", self.date_to), ("date_to", "=", False)])
        if domain_list and not self.crossovered_budget_id.filtered_domain(AND(domain_list)):
            self.crossovered_budget_id = self.env["crossovered.budget"].search(AND(domain_list), limit=1)

    @api.onchange("crossovered_budget_id")
    def _onchange_crossovered_budget_id(self):
        if self.crossovered_budget_id:
            self.date_from = self.date_from or self.crossovered_budget_id.date_from
            self.date_to = self.date_to or self.crossovered_budget_id.date_to

    @api.onchange("period")
    def _on_change_fiscal_year(self):
        for record in self.filtered("period"):
            record.date_from = record.period.date_from
            record.date_to = record.period.date_to

    @api.constrains("general_budget_id", "analytic_account_id")
    def _must_have_analytical_or_budgetary_or_both(self):
        for record in self:
            if not record.analytic_account_id and not record.general_budget_id:
                raise ValidationError(
                    _("You have to enter at least a budgetary position or analytic account on a budget line.")
                )

    @api.constrains("date_from", "date_to")
    def _line_dates_between_budget_dates(self):
        for line in self:
            if line.date_from and line.date_to and line.date_from > line.date_to:
                raise ValidationError(_("Budget line end date may not be before start date."))
            budget_date_from = line.crossovered_budget_id.date_from
            budget_date_to = line.crossovered_budget_id.date_to
            if line.date_from and (
                (budget_date_from and line.date_from < budget_date_from)
                or (budget_date_to and line.date_from > budget_date_to)
            ):
                raise ValidationError(
                    _('"Start Date" of the budget line should be included in the period of the budget.')
                )
            if line.date_to and (
                (budget_date_from and line.date_to < budget_date_from)
                or (budget_date_to and line.date_to > budget_date_to)
            ):
                raise ValidationError(
                    _('"End Date" of the budget line should be included in the period of the budget.')
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("budget_line_details"):
                self.validate_budget_lines(vals)

        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            record._ensure_detail_lines(vals)
        return records

    def _ensure_detail_lines(self, vals=None):
        self.ensure_one()
        accounts = self.general_budget_id.account_ids
        if not accounts:
            return

        existing_account_ids = set(self.budget_line_details.mapped("account").ids)
        for account in accounts:
            if account.id in existing_account_ids:
                continue
            self.env["crossovered.budget.lines.detail"].create(
                {
                    "budgetary_position_id": self.id,
                    "account": account.id,
                    "budget_amount": 0.0,
                }
            )

    def _iter_detail_accounts_from_vals(self, vals):
        for command in vals.get("budget_line_details", []):
            if not isinstance(command, (list, tuple)) or len(command) < 3:
                continue
            if command[0] in (0, 1) and isinstance(command[2], dict):
                account_id = command[2].get("account")
                if account_id:
                    yield account_id

    def validate_budget_lines(self, vals):
        budget_post = self.env["account.budget.post"].browse(vals.get("general_budget_id"))
        allowed_accounts = set(budget_post.account_ids.ids)
        for account_id in self._iter_detail_accounts_from_vals(vals):
            if account_id not in allowed_accounts:
                raise ValidationError(_("Budget line not found in budget category definition."))

    def _recompute_totals_from_details(self):
        for line in self:
            detail_lines = line.budget_line_details
            line.write(
                {
                    "planned_amount": sum(detail_lines.mapped("budget_amount")),
                    "commitment_budget": sum(detail_lines.mapped("commitment_budget")),
                    "reallaocation_addition": sum(detail_lines.mapped("reallaocation")),
                    "addition": sum(detail_lines.mapped("addition")),
                    "revised_budget": sum(detail_lines.mapped("revised_budget")),
                }
            )

    def open_detail_budget(self):
        view = self.env.ref("droga_bd.crossovered_budget_lines_view_form")
        return {
            "name": _("Budget Detail"),
            "view_mode": "form",
            "res_model": "crossovered.budget.lines",
            "view_id": view.id,
            "type": "ir.actions.act_window",
            "res_id": self.id,
            "target": "new",
        }

    def action_open_budget_entries(self):
        self.ensure_one()
        if self.analytic_account_id:
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "analytic.account_analytic_line_action_entries"
            )
            action["domain"] = [
                ("account_id", "=", self.analytic_account_id.id),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ]
            if self.general_budget_id:
                action["domain"] += [("general_account_id", "in", self.general_budget_id.account_ids.ids)]
        else:
            action = self.env["ir.actions.act_window"]._for_xml_id("account.action_account_moves_all_a")
            action["domain"] = [
                ("account_id", "in", self.general_budget_id.account_ids.ids),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ]
        return action

    def unlink(self):
        for record in self:
            if record.planned_amount or record.reallaocation_addition or record.addition:
                raise ValidationError(_("You can't delete budget record, it contains budget data."))
        return super().unlink()

    def update_budget_period(self):
        for record in self.search([("period", "!=", False)]):
            record.date_from = record.period.date_from
            record.date_to = record.period.date_to


class CrossoveredBudgetLinesDetail(models.Model):
    _name = "crossovered.budget.lines.detail"
    _description = "Budget Line Detail"
    _order = "account asc"

    budgetary_position_id = fields.Many2one("crossovered.budget.lines")
    crossovered_budget_id = fields.Many2one(related="budgetary_position_id.crossovered_budget_id", store=True)
    general_budget_id = fields.Many2one(related="budgetary_position_id.general_budget_id", store=True)
    date_from = fields.Date(related="crossovered_budget_id.date_from", store=True)
    date_to = fields.Date(related="crossovered_budget_id.date_to", store=True)
    company_id = fields.Many2one(related="crossovered_budget_id.company_id", store=True)

    account = fields.Many2one("account.account")
    budget_amount = fields.Float("Budget Amount")
    commitment_budget = fields.Float("Commitment")
    reallaocation = fields.Float("Reallocation +/-")
    addition = fields.Float("Addition")
    revised_budget = fields.Float("Revised", compute="calculate_budget", store=True)
    actual = fields.Float("Actual", compute="calculate_budget", store=True)
    remaining_balance = fields.Float("Remaining", compute="calculate_budget", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("budgetary_position_id")._recompute_totals_from_details()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.mapped("budgetary_position_id")._recompute_totals_from_details()
        return res

    def unlink(self):
        for record in self:
            if record.budget_amount or record.reallaocation or record.addition:
                raise ValidationError(_("You can't delete budget record, it contains budget data."))
        parents = self.mapped("budgetary_position_id")
        res = super().unlink()
        parents._recompute_totals_from_details()
        return res

    def load_commitment_budget(self):
        budget_lines = self.env["crossovered.budget.lines"].search([("crossovered_budget_state", "!=", "cancel")])

        for budget in budget_lines:
            for line in budget.budget_line_details:
                commitment_budgets = self.env["droga.budget.commitment.budget"].search(
                    [
                        ("state", "=", "Active"),
                        ("budgetary_position", "=", budget.general_budget_id.id),
                        ("budget_date", ">=", budget.crossovered_budget_id.date_from),
                        ("budget_date", "<=", budget.crossovered_budget_id.date_to),
                        ("expense_account", "=", line.account.id),
                        ("analytic_account_id", "=", budget.analytic_account_id.id),
                    ]
                )

                account_commitment_budget = 0
                for commitment_budget in commitment_budgets:
                    if commitment_budget.document_type == "PR":
                        account_commitment_budget += commitment_budget.purchase_request_total_amount
                    else:
                        account_commitment_budget += commitment_budget.purchase_order_total_amount

                if account_commitment_budget:
                    line.write({"commitment_budget": account_commitment_budget * -1})

    def calculate_remaining_budget(self):
        budgets = self.env["crossovered.budget"].search([("state", "!=", "cancel")])
        for budget in budgets:
            for line in budget.crossovered_budget_line:
                line.write({"remaining_balance": line.revised_budget + line.practical_amount})

    def calculate_remaining_budget_detail(self):
        budgets = self.env["crossovered.budget.lines"].search([("crossovered_budget_state", "!=", "cancel")])
        for record in budgets.budget_line_details:
            revised_budget = (
                record.budget_amount + record.commitment_budget + record.reallaocation + record.addition
            )

            actual_expense = self.env["account.move.line"].search(
                [
                    ("company_id", "=", record.company_id.id),
                    ("account_id", "=", record.account.id),
                    ("date", ">=", record.date_from),
                    ("date", "<=", record.date_to),
                    ("parent_state", "=", "posted"),
                ]
            )

            analytic_account_id = record.budgetary_position_id.analytic_account_id.id
            actual = 0
            for line in actual_expense:
                for analytic_line in line.analytic_line_ids:
                    if analytic_account_id == analytic_line.account_id.id:
                        actual += line.balance

            remaining_balance = revised_budget - actual
            record.write(
                {
                    "revised_budget": revised_budget,
                    "actual": actual,
                    "remaining_balance": remaining_balance,
                }
            )

    @api.depends("budget_amount", "commitment_budget", "reallaocation", "addition")
    def calculate_budget(self):
        for record in self:
            revised_budget = (
                record.budget_amount + record.commitment_budget + record.reallaocation + record.addition
            )

            analytic_account_id = record.budgetary_position_id.analytic_account_id.id
            actual_expense = self.env["account.move.line"].search(
                [
                    ("company_id", "=", record.company_id.id),
                    ("account_id", "=", record.account.id),
                    ("date", ">=", record.date_from),
                    ("date", "<=", record.date_to),
                    ("parent_state", "=", "posted"),
                ]
            )

            actual = 0
            for line in actual_expense:
                for analytic_line in line.analytic_line_ids:
                    if analytic_account_id == analytic_line.account_id.id:
                        actual += line.balance

            record.revised_budget = revised_budget
            record.actual = actual
            record.remaining_balance = revised_budget - actual

    @api.onchange("account")
    def on_account_change(self):
        if self.general_budget_id:
            return {"domain": {"account": [("id", "in", self.general_budget_id.account_ids.ids)]}}
        return {"domain": {"account": []}}
