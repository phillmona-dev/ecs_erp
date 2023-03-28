from odoo import models,fields

class droga_export_status(models.Model):
    _name='droga.export.status'
    status_origin_sales = fields.Many2one('sale.order', readonly=True)
    status=fields.Char('Status')
    completed=fields.Boolean('Completed',default=False)
    remark=fields.Char('Remark')

class droga_export_status_list(models.Model):
    _name='droga.export.status.list'
    status_list=fields.Char('Status')
    status = fields.Selection([('Active', 'Active'), ('Closed', 'Closed')],required=True,default='Active')