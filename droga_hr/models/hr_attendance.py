from odoo import models, fields, api
from datetime import datetime


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    attendance_machine_trans_id = fields.Char("Attendance Machine Trans ID")
    attendance_date = fields.Date("Attendance Date")

    real_worked_hours = fields.Float(string="Real Work Hours", compute="compute_real_worked_hours")

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
