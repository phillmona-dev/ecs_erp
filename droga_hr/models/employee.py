from odoo import models, fields


class Employee(models.Model):
    _inherit = 'hr.employee'

    amharic_name = fields.Char("ሙሉ ስም")
    amharic_position = fields.Char("የስራ መደብ")
    hire_date_ec = fields.Char("የቅጥር ቀን")


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    amharic_name = fields.Char("ሙሉ ስም")
    amharic_position = fields.Char("የስራ መደብ")
    hire_date_ec = fields.Char("የቅጥር ቀን")
