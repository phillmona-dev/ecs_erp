from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    attendance_machine_trans_id = fields.Char("Attendance Machine Trans ID")
    attendance_date = fields.Date("Attendance Date")

    real_worked_hours = fields.Float(string="Real Work Hours", compute="compute_real_worked_hours")

    employee_badge_id = fields.Char(related='employee_id.barcode', string='Badge ID')
    department = fields.Char(related='employee_id.department_name', string='Department')

    @api.model
    def create(self, vals):
        # search record for the current employee

        check_in = datetime.strptime(str(vals['check_in']), '%Y-%m-%d %H:%M:%S')
        check_in = check_in.strftime('%Y-%m-%d')

        employee_id = vals['employee_id']
        check_in_record = self.env["hr.attendance"].search(
            [('check_in', '<=', check_in), ('check_in', '>=', check_in), ('employee_id', '=', employee_id)])

        if check_in_record:
            raise ValidationError("You can't create check in more than once!")
        else:
            res = super(Attendance, self).create(vals)
            return res

    def update_not_checked_out_records(self):
        dt = datetime.utcnow()
        check_in = dt.strftime('%Y-%m-%d')

        attendances = self.env['hr.attendance'].search([('check_out', '=', False)])
        for attendance in attendances:
            attendance['check_out'] = attendance['check_in']

    @api.depends('worked_hours')
    def compute_real_worked_hours(self):
        for record in self:
            record.real_worked_hours = 1
            date_object = record.check_in
            if record.worked_hours == 0:
                record.real_worked_hours = 0
            elif date_object.weekday() in [5, 6]:
                record.real_worked_hours = record.worked_hours
            else:
                record.real_worked_hours = record.worked_hours - 1
