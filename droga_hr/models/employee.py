from odoo import models, fields, api
from datetime import datetime, timedelta


class Employee(models.Model):
    _inherit = 'hr.employee'

    _order = 'barcode asc'

    amharic_name = fields.Char("ሙሉ ስም")
    amharic_position = fields.Char("የስራ መደብ")
    hire_date_ec = fields.Char("የቅጥር ቀን")

    hire_date = fields.Date("Hire Date")
    retire_date = fields.Date("Retire Date", compute="compute_retire_date")
    department_name = fields.Char(related='department_id.name', store=True)

    bank = fields.Many2one('res.bank', string="Bank")
    bank_account = fields.Char("Bank Account")
    contract_type = fields.Many2one("hr.contract.type", string="Contract Type")

    is_attendance_required = fields.Boolean("Attendance Required", default=True)
    check_in = fields.Boolean("Check In", default=True)
    check_out = fields.Boolean("Check Out", default=True)

    division = fields.Many2one("droga.hr.division", "Division")

    tin_no = fields.Char('Tin')
    pension_no = fields.Char('Pension No')

    @api.model
    def create(self, vals):
        # Generate automatic employee ID when barcode is not explicitly set.
        if not vals.get('barcode'):
            vals['barcode'] = self.env['ir.sequence'].next_by_code('employee.id') or '/'

        res = super(Employee, self).create(vals)

        return res

    @api.depends("birthday")
    def compute_retire_date(self):
        for record in self:
            # assign default date
            record.retire_date = None
            if record.birthday:
                record.retire_date = record.birthday + timedelta(days=365.25 * 60)


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    amharic_name = fields.Char("ሙሉ ስም")
    amharic_position = fields.Char("የስራ መደብ")
    hire_date_ec = fields.Char("የቅጥር ቀን")

    hire_date = fields.Date("Hire Date")

    bank = fields.Many2one('res.bank', string="Bank")
    bank_account = fields.Char("Bank Account")
    department_name = fields.Char(related='department_id.name', store=True)
    contract_type = fields.Many2one("hr.contract.type", string="Contract Type")
    is_attendance_required = fields.Boolean("Attendance Required", default=True)
    check_in = fields.Boolean("Check In", default=True)
    check_out = fields.Boolean("Check Out", default=True)

    division = fields.Many2one("droga.hr.division", "Division")

    tin_no = fields.Char('Tin')
    pension_no = fields.Char('Pension No')
