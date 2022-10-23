from odoo import models, fields, api


class droga_location_extension(models.Model):
    _inherit = 'stock.location'
    con_type = fields.Selection([
        ('CONI', 'Consignment customer location'),
        ('CONR', 'Consignment vendor location'),
        ('SIF', 'Free sample'),
        ('SIR', 'Sample to be returned'),
        ], string='Cons/sample Type')

class droga_stock_picking_extension(models.Model):
    _inherit = 'stock.picking'

    trans_issue_request=fields.Many2one('droga.inventory.transfer.custom','Transfer request')
    cons_sample_issue_request = fields.Many2one('droga.inventory.consignment.issue','Cons/sample issue request')
    cons_receive_request = fields.Many2one('droga.inventory.consignment.receive','Consignment receive request')
    state = fields.Selection(selection_add=[('processed', 'Processed')])


    def button_validate(self):
        if self.origin:
            if self.origin.startswith('MTIV') :
                self.state='processed'
                trans_requests=self.env['droga.inventory.transfer.custom'].search([('name','=',self.origin)])
                for rec in trans_requests:
                    trans_requests.state='processed'
        else:
            super(droga_stock_picking_extension, self).button_validate()



class droga_stock_product_extension(models.Model):
    _inherit = 'product.template'
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default='', group_expand='_read_group_categ_id',
        required=True, help="Select category for the current product")
    default_code = fields.Char('Internal Reference',compute='_compute_default_code',
        inverse='_compute_default_code',
         store=True,required=True)
    def _compute_default_code(self):
        pass
    property_stock_inventory = fields.Many2one(
        'stock.location', "Inventory Location",
        company_dependent=True, check_company=True,default='',
        domain="[('usage', '=', 'internal'), '|', ('company_id', '=', False), ('company_id', '=', allowed_company_ids[0])]")
    emergency_order_point=fields.Float('Emergency order point')
    maximum_stock_level = fields.Float('Maximum stock level')
    average_month_consumption = fields.Float('Avg. monthly cons.',compute='_get_avg_monthly_consumption',help="Average monthly consumption")
    def _get_avg_monthly_consumption(self):
        for rec in self:
            rec.average_month_consumption=0
