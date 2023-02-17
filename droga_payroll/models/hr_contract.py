from odoo import models, fields, api


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
