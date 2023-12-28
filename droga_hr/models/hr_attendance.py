from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    attendance_machine_trans_id = fields.Char("Attendance Machine Trans ID")
    attendance_date = fields.Date("Attendance Date", default=datetime.now().date())

    real_worked_hours = fields.Float(string="Real Work Hours", compute="compute_real_worked_hours")

    employee_badge_id = fields.Char(related='employee_id.barcode', string='Badge ID')
    department = fields.Char(related='employee_id.department_name', string='Department')
    attendance_from = fields.Selection([('Attendance Machine', 'Attendance Machine'), ('Kiosk Mode', 'Kiosk Mode')],
                                       default='Attendance Machine', string='Attendance From')

    @api.model
    def create(self, vals):
        # search record for the current employee

        check_in = datetime.strptime(str(vals['check_in']), '%Y-%m-%d %H:%M:%S')
        check_in = check_in.strftime('%Y-%m-%d')

        employee_id = vals['employee_id']
        check_in_record = self.env["hr.attendance"].search(
            [('check_in', '<=', check_in), ('check_in', '>=', check_in), ('employee_id', '=', employee_id)])

        if 'attendance_date' in vals:
            vals["attendance_from"] = "Attendance Machine"
        else:
            vals["attendance_from"] = "Kiosk Mode"

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


class AttendanceReport(models.Model):
    _name = 'droga.hr.attendance.report'

    order = "date desc"

    employee_id = fields.Many2one("hr.employee")
    employee_badge_id = fields.Char(related='employee_id.barcode', string='Badge ID')
    date = fields.Date("Attendance Day")
    check_in = fields.Datetime("Check In")
    check_out = fields.Datetime("Check Out")
    day_count = fields.Float("Day Count")
    is_absent = fields.Boolean("Absent", default=False)
    absence_reason = fields.Char("Reason")
    company_id = fields.Many2one("res.company")
    late_minute = fields.Float("Late Minute")
    worked_hours = fields.Float("Worked Hours")
    real_worked_hours = fields.Float("Real Worked Hours")

    def update_attendance_report(self):
        # get active employees
        vals = {}

        # start_day_str = '2023-12-27'
        # start_day_str = datetime.now().date()
        # start_day = datetime.strptime(str(start_day_str), "%Y-%m-%d").date()
        # Get the current day
        current_day = datetime.now().date()

        active_employees = self.env["hr.employee"].search([('active', '=', True)])

        for employee in active_employees:

            # Define the loop range using timedelta
            day = start_day

            while day <= current_day:

                # check for sunday
                if day.weekday() == 6:
                    day += timedelta(days=1)
                    continue

                emp_attendances = self.env["hr.attendance"].search(
                    [('employee_id', '=', employee.id), ('attendance_date', '=', day)])

                attendance_report = self.env['droga.hr.attendance.report'].search(
                    [('employee_id', '=', employee.id), ('date', '=', day)])

                if len(emp_attendances) == 0 and len(attendance_report) == 0:
                    # create absent record
                    vals["employee_id"] = employee.id
                    vals["date"] = day
                    vals["is_absent"] = True
                    vals["absence_reason"] = "Not Showed Up"
                    vals["company_id"] = employee.company_id.id
                    vals["late_minute"] = 0
                    vals["check_in"] = None
                    vals["check_out"] = None
                    vals["worked_hours"] = 0
                    vals["real_worked_hours"] = 0

                    self.env["droga.hr.attendance.report"].create(vals)

                for attendance in emp_attendances:

                    check_in_time = datetime.strptime(str(attendance.check_in), '%Y-%m-%d %H:%M:%S')

                    minutes_late = 0
                    is_absent = False
                    absence_reason = ""
                    real_worked_hours = 0

                    real_worked_hours = self.compute_real_worked_hours(attendance)

                    # Calculate five minutes late
                    if check_in_time.hour >= 5:
                        minutes_late = check_in_time.minute
                    if minutes_late > 30 and attendance.worked_hours == 0:
                        is_absent = True
                        absence_reason = "Late >30 Min & No Check Out"
                    elif minutes_late > 30 and attendance.worked_hours != 0:
                        absence_reason = "Late >30 Min"
                        is_absent = True
                    elif attendance.worked_hours == 0:
                        absence_reason = "No Check Out"
                        is_absent = True
                    else:
                        is_absent = False
                        absence_reason = "Showed Up"

                    if len(attendance_report) == 0:  # insert new record

                        vals["employee_id"] = employee.id
                        vals["date"] = day
                        vals["is_absent"] = is_absent
                        vals["absence_reason"] = absence_reason
                        vals["company_id"] = employee.company_id.id
                        vals["late_minute"] = minutes_late
                        vals["check_in"] = attendance.check_in
                        vals["check_out"] = attendance.check_out
                        vals["worked_hours"] = attendance.worked_hours
                        vals["real_worked_hours"] = real_worked_hours

                        self.env["droga.hr.attendance.report"].create(vals)

                    else:  # update record

                        attendance_report.write(
                            {'is_absent': is_absent, 'absence_reason': absence_reason,
                             'check_in': attendance.check_in,
                             'check_out': attendance.check_out, 'late_minute': minutes_late,
                             'real_worked_hours': real_worked_hours})

                # Move to the next day
                day += timedelta(days=1)

    def compute_real_worked_hours(self, attendance):
        for record in attendance:
            date_object = record.check_in
            if record.worked_hours == 0:
                return 0
            elif date_object.weekday() in [5, 6]:
                return record.worked_hours
            else:
                return record.worked_hours - 1
