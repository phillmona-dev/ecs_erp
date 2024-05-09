from odoo import models, fields, api
from datetime import date


class HrContract(models.Model):
    _inherit = 'hr.contract'

    housing_allowance = fields.Float("Housing Allowance", default=0, tracking=True)
    transport_allowance = fields.Float("Transport Allowance", default=0)
    representation_allowance = fields.Float("Representation Allowance", default=0)
    fuel_allowance = fields.Float("Fuel Allowance", default=0)
    acting_allowance = fields.Float("Acting Allowance", default=0)
    telephone_allowance = fields.Float("Telephone Allowance", default=0)
    pension_contribution = fields.Boolean("Contribute Pension", default=True)
    sales = fields.Boolean("Sales",
                           help="For sales transport allowance upto 2200 is not taxable for others it is upto 600")
    canteen = fields.Boolean("Uses Canteen Service", help="If the employee uses canteen service tick the check box");

    custom_salary_structure = fields.Boolean("Custom Salary Structure", default=False)
    salary_structure = fields.One2many(related="job_id.salary_structure")
    salary_structure_custom = fields.One2many("hr.job.salary", "contract_id")

    # sales commission
    sales_commission = fields.Float("Sales Commission")

    # get contract rate
    def get_employee_rate(self, payment_code):
        amount = 0
        for record in self:
            if record.state == 'open':
                if record.custom_salary_structure:  # get rate from custom salary structure

                    salary_structures = record.salary_structure_custom

                    for salary_structure in salary_structures:
                        if salary_structure.date_to >= date.today():
                            rates = salary_structure.salary_detail
                            for rate in rates:
                                if rate.payment_type.code == payment_code:
                                    amount = rate.amount
                else:  # get rate from main salary structure
                    salary_structures = record.salary_structure

                    for salary_structure in salary_structures:

                        if salary_structure.date_to >= date.today():
                            rates = salary_structure.salary_detail
                            for rate in rates:
                                if rate.payment_type.code == payment_code:
                                    amount = rate.amount

        return amount
