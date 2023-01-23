from odoo import models, fields


class Employee(models.Model):
    _inherit = 'hr.employee'

    pos_device_ip_address = fields.Char("POS IP Address")


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    pos_device_ip_address = fields.Char("POS IP Address")
