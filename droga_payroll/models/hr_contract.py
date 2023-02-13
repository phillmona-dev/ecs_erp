from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    housing_allowance = fields.Float("Housing Allowance", default=0)
    transport_allowance = fields.Float("Transport Allowance", default=0)
    representation_allowance = fields.Float("Representation Allowance", default=0)
    fuel_allowance = fields.Float("Fuel Allowance", default=0)
    acting_allowance = fields.Float("Acting Allowance", default=0)
