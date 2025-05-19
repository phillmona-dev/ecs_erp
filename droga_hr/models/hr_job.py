from odoo import models, fields, api
from datetime import timedelta


class HrJob(models.Model):
    _inherit = 'hr.job'

    salary_structure = fields.One2many("hr.job.salary", "job_id")
    job_grade = fields.Many2one("hr.job.grade")
    currency = fields.Many2one("res.currency", string="Currency")

    # _sql_constraints = [('name_unique', 'unique(name)', 'Job position must be unique')]

    def close_old_salary_structures(self):
        jobs = self.env['hr.job'].search([])

        for job in jobs:
            active_structures = job.salary_structure.filtered(lambda s: s.state == 'Active')
            if len(active_structures) == 2:
                # get minium date_from active_structures
                # Sort by date_from (ascending, None last)
                sorted_structures = active_structures.sorted(
                    key=lambda s: s.date_from or fields.Date.today()
                )
                earliest_structure = sorted_structures[0]
                active_structure = sorted_structures[1]

                # calculate closing date
                closing_date = active_structure.date_from - timedelta(days=1)

                # close the earliest active salary structure
                earliest_structure.write({'state': 'Closed', 'date_to': closing_date})


class HrJobSalary(models.Model):
    _name = 'hr.job.salary'
    _order = 'date_from'

    job_id = fields.Many2one("hr.job")
    contract_id = fields.Many2one("hr.contract")
    name = fields.Char("Description", required=True)
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    state = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], default="Active",
                             required=True)
    salary_detail = fields.One2many("hr.job.salary.detail", "job_detail_id")
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)
    currency = fields.Many2one("res.currency", string="Currency")


class HrJobSalaryDetail(models.Model):
    _name = 'hr.job.salary.detail'

    job_detail_id = fields.Many2one("hr.job.salary")
    payment_type = fields.Many2one("hr.job.salary.payment", required=True)
    date_from = fields.Date("Date From")
    date_to = fields.Date("Date To")
    amount = fields.Float("Amount", required=True)
    state = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], default="Active",
                             required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    def update_status_from_parent(self):
        details = self.env["hr.job.salary.detail"].search([])
        for record in details:
            if record.job_detail_id.state == 'Closed':
                record.write({'state': 'Closed'})


class HrJobSalaryPayment(models.Model):
    _name = 'hr.job.salary.payment'

    code = fields.Char("Code", required=True)
    name = fields.Char("Name", required=True)
    state = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], default="Active",
                             required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    _sql_constraints = [('code_unique', 'unique(code)', 'Code must be unique')]


class HrJobCrade(models.Model):
    _name = "hr.job.grade"

    name = fields.Char("Code", required=True)
    description = fields.Char("Description", required=True)
    state = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active')
