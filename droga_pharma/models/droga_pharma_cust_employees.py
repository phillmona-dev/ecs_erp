from odoo import models, fields

class droga_pharma_customer(models.Model):
    _inherit='res.partner'
    allowed_product_groups = fields.Many2many('product.category')
    employees = fields.One2many('droga.pharma.cust.employees', 'parent_customer')

class droga_pharma_customer_employees(models.Model):
    _name = 'droga.pharma.cust.employees'
    _rec_name = 'descr'
    descr = fields.Char('descr', compute='_get_descr')
    parent_customer = fields.Many2one('res.partner', string='Customer Name')
    employer_name = fields.Char(related='parent_customer.name', store=True)
    employee_name = fields.Char('Employee Name', required=True)
    mobile = fields.Char('Mobile')
    gender = fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Gender')
    job_position = fields.Char(string='Job position')

    additional_product_groups=fields.Many2many('product.category')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    max_amount=fields.Float(string='Max amount')
    from_date=fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    amount_valid_for=fields.Float(string='Period')
    amount_valid_type = fields.Selection(
        [('Day', 'Day'), ('Month', 'Month'),('Year', 'Year')],
        string='Period type')
    remaining_amount_period=fields.Char(string='Remaining',compute='_remain_amount_period')
    def _remain_amount_period(self):
        for rec in self:
            rec.remaining_amount_period='FIX ME'

    def _get_descr(self):
        for record in self:
            try:
                name = (record.job_position + ' - ') if record.job_position else ''

                record.descr = name + record.employee_name
            except:
                record.descr = record.employee_name if record.employee_name else ' '

class droga_physiotherapist_list(models.Model):
    _name='droga.physiotherapist.list'
    _rec_name='physiotherapist_name'
    physiotherapist_name = fields.Many2one('hr.employee', string='Physiotherapist Name',required=True)
    branch=fields.Selection([('PT-4 Kilo', '4 kilo branch'), ('PT-Bole', 'Bole branch')], required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active')
