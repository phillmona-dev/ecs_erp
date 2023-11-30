from odoo import models, fields, api
from datetime import datetime


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    attendance_machine_trans_id = fields.Char("Attendance Machine Trans ID")
    attendance_date = fields.Date("Attendance Date")

    def update_not_checked_out_records(self):
        dt = datetime.utcnow()
        check_in = dt.strftime('%Y-%m-%d')

        attendances = self.env['hr.attendance'].search([('check_out', '=', False)])
        for attendance in attendances:
            attendance['check_out'] = attendance['check_in']
