from odoo import _, api, fields, models


class CrossoveredBudgetLines(models.Model):

    _inherit = "crossovered.budget.lines"

    commitment_budget = fields.Float('Commitment Budget')
    remaining_balance = fields.Float('Remaining Balance')

    def load_commitment_budget(self):
        # get active budgets
        budgets = self.env['crossovered.budget'].search(
            [('state', '!=', 'cancel')])

        for budget in budgets:
            for line in budget.crossovered_budget_line:
                # search commitment budget
                total_commitment = 0
                remaining_balance = 0
                commitment_budgets = self.env['droga.budget.commitment.budget'].search(
                    [('state', '=', 'Active'), ('budgetary_position', '=', line.general_budget_id.id),
                     ('budget_date', '>=', line.date_from), ('budget_date', '<=', line.date_to)])

                if commitment_budgets:
                    for commitment_budget in commitment_budgets:
                        total_commitment += commitment_budget.purchase_order_total_amount + \
                            commitment_budget.purchase_request_total_amount

                    # update budget line
                    if total_commitment != 0:
                        line.write({'commitment_budget': total_commitment*-1})

                    # calculate remaining balance
                remaining_balance = line.planned_amount + line.practical_amount+line.commitment_budget
                line.write({'remaining_balance': remaining_balance})
