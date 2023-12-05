from odoo import fields,models

class points_storage(models.Model):
    _name='droga.pharma.points.earned'

    customer=fields.Many2one('res.partner')
    point_type=fields.Char('Point type')
    sales_ref=fields.Many2one('sale.order',string='Sales order')
    earned_date=fields.Date('Date')
    points_earned = fields.Float('Points earned')

    def open_sales(self):
        return {
            'name': 'Sales order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': self.env.ref('droga_pharma.view_order_form_pharma').id,
            'type': 'ir.actions.act_window',

            'res_id': self.sales_ref.id,
        }