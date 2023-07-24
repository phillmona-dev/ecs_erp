from odoo import models,fields,api

class Attendance(models.Model):
    _inherit = 'hr.attendance'

    attendance_machine_trans_id=fields.Char("Attendance Machine Trans ID")
