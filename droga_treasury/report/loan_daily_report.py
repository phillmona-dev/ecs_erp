import imp


from odoo import _, api, fields, models

class LoanDailyReport(models.Model):
    _name = 'droga.loan.daily.report'
    _description = 'Report that show loan daily report'

    
    