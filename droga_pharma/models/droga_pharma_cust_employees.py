import datetime

from odoo import models, fields, api


class droga_pharma_customer(models.Model):
    _inherit='res.partner'
    allowed_product_groups = fields.Many2many('product.category')
    employees = fields.One2many('droga.pharma.cust.employees', 'parent_customer')

class droga_pharma_customer_employees(models.Model):
    _name = 'droga.pharma.cust.employees'

    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    _rec_name = 'descr'
    sales=fields.One2many('sale.order','customer_emp')
    sales_detail=fields.One2many('sale.order.line',related='sales.order_line')

    descr = fields.Char('descr', compute='_get_descr')
    parent_customer = fields.Many2one('res.partner', string='Customer Name')
    employer_name = fields.Char(related='parent_customer.name', store=True)
    employee_name = fields.Char('Employee Name', required=True)
    mobile = fields.Char('Mobile')
    gender = fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Gender',tracking=True)
    job_position = fields.Char(string='Job position')
    profession=fields.Selection(
        [('hp', 'Health professional'),('other', 'Other')],
        string='Profession')
    age = fields.Integer(compute='_compute_age')
    dob = fields.Date('Date of birth', default=datetime.date.today(),tracking=True)
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
    childs=fields.One2many('droga.pharma.child','parent',string='Childs')

    def open_children(self):
        return {
            'name': 'Children',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'droga.pharma.cust.employees',
            'view_id': self.env.ref('droga_pharma.droga_pharma_children').id,
            'type': 'ir.actions.act_window',

            # This will pass the detail ID if a record is present
            'res_id': self.id,
            'target': 'new',
        }

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

    @api.depends('dob')
    def _compute_age(self):
        for record in self:
            if record.dob:
                today = datetime.date.today()
                # Check if the date has passed this year
                if today.strftime("%m%d") >= record.dob.strftime("%m%d"):
                    record['age'] = today.year - record.dob.year
                else:
                    record['age'] = today.year - record.dob.year - 1
            else:
                record['age'] = 0

class droga_physiotherapist_list(models.Model):
    _name='droga.physiotherapist.list'
    _rec_name='physiotherapist_name'
    physiotherapist_name = fields.Many2one('hr.employee', string='Physiotherapist Name',required=True)
    branch=fields.Selection([('PT-4 Kilo', '4 kilo branch'), ('PT-Bole', 'Bole branch')], required=True)
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')], required=True, default='Active')

class droga_pharma_child_list(models.Model):
    _name='droga.pharma.child'
    gender = fields.Selection(
        [('Male', 'Male'), ('Female', 'Female')],
        string='Child gender', tracking=True)
    child_dob= fields.Date('Child dob', default=datetime.date.today(),tracking=True)
    child_name=fields.Char('Child name')
    breast_feed_days=fields.Float('Breastfeed period in days',default=180)
    parent=fields.Many2one('droga.pharma.cust.employees',string='Parent')
