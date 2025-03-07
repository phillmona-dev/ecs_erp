from datetime import datetime, timedelta
from odoo import models, fields, api

class CustomerGradeUpdater(models.Model):
    _inherit = 'res.partner'
    cust_grade = fields.Many2one('droga.cust.grade', string='Customer Grade', tracking=True)

    def _compute_customer_grade(self):
        """Method to evaluate and assign customer grade based on the last 3 months' sales."""
        num_of_days = self.env['ir.config_parameter'].get_param('grade_num_of_days', 0)
        gradea = self.env['ir.config_parameter'].get_param('grade_a', 0)
        gradeb = self.env['ir.config_parameter'].get_param('grade_b', 0)
        gradec = self.env['ir.config_parameter'].get_param('grade_c', 0)
        three_months_ago = fields.Datetime.today() - timedelta(days=num_of_days)  # Get date 3 months ago

        for customer in self.search([]):  # Fetch all customers
            total_purchases = customer._get_total_purchases(three_months_ago)

            if total_purchases >= gradea:
                grade = 'A'
            elif total_purchases >= gradeb:
                grade = 'B'
            elif total_purchases >= gradec:
                grade = 'C'
            else:
                grade = 'D'

            # Find the corresponding grade record
            grade_record = self.env['droga.cust.grade'].search([('grade', '=', grade)], limit=1)
            if grade_record:
                customer.cust_grade = grade_record.id

    def _get_total_purchases(self, start_date):
        """Fetch total purchases for the last 3 months."""
        orders = self.env['sale.order'].search([
            ('partner_id', '=', self.id),
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', start_date)
        ])
        total_amount = sum(orders.mapped('amount_total'))
        return total_amount