from odoo import models, fields, api
from datetime import date, timedelta


class droga_pharma_stock_card(models.TransientModel):
    _name = 'droga.pharma.itr'
    _descr = 'Inventory turn over rate'

    branch = fields.Many2one('stock.warehouse', 'Warehouse')
    product = fields.Many2one('product.product', 'Product')
    date_from = fields.Date('Date from', default=fields.Date.today()-timedelta(days=365))
    date_to = fields.Date('Date to', default=fields.Date.today())

    results=fields.One2many('droga.pharma.itr.detail','header')

    def load_results(self):
        self.results.unlink()

        if self.product:
            prod_id=self.product.product_variant_id
            avg=self.get_avg(prod_id.id)
            qogs=self.get_qgs(prod_id.id)
            if avg==0:
                val = {
                    'header': self.id,
                    'product': self.product.id,
                    'cogs': qogs,
                    'av_inv': avg,
                    'inv_tur': 0,
                    #TODO - Add DSI, check with GET and add it
                }
                self.results.create(val)
            else:
                itr=qogs/self.get_avg(prod_id.id)
                val = {
                    'header': self.id,
                    'product': self.product.id,
                    'cogs': qogs,
                    'av_inv': avg,
                    'inv_tur': itr,
                    # TODO - Add DSI, check with GET and add it
                }
                self.results.create(val)
        else:
            products=self.env['stock.quant'].search([('location_id.warehouse_id','=',self.branch.id)]).mapped('product_id')
            for prod_id in products:

                if not prod_id:
                    continue

                avg = self.get_avg(prod_id.id)
                qogs = self.get_qgs(prod_id.id)
                if avg == 0:
                    val = {
                        'header': self.id,
                        'product': prod_id.product_tmpl_id.id,
                        'cogs': qogs,
                        'av_inv': avg,
                        'inv_tur': 0,
                        # TODO - Add DSI, check with GET and add it
                    }
                    self.results.create(val)
                else:
                    itr = qogs / self.get_avg(prod_id.id)
                    val = {
                        'header': self.id,
                        'product': prod_id.product_tmpl_id.id,
                        'cogs': qogs,
                        'av_inv': avg,
                        'inv_tur': itr,
                        # TODO - Add DSI, check with GET and add it
                    }
                    self.results.create(val)

    def get_avg(self,product_id):

        month1 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=334))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=334))]).mapped('qty_done'))
        month2 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=304))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=304))]).mapped('qty_done'))
        month3 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=273))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=273))]).mapped('qty_done'))
        month4 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=243))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=243))]).mapped('qty_done'))
        month5 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=213))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=213))]).mapped('qty_done'))
        month6 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=182))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=182))]).mapped('qty_done'))
        month7 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=152))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=152))]).mapped('qty_done'))
        month8 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=122))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=122))]).mapped('qty_done'))
        month9 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=91))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=91))]).mapped('qty_done'))
        month10 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=60))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=60))]).mapped('qty_done'))
        month11 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=30))]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                     ('date', '<',
                                                                      fields.Date.today() - timedelta(
                                                                          days=30))]).mapped('qty_done'))
        month12 = sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_dest_id.warehouse_id','=',self.branch.id),
                                                                      ('date', '<',
                                                                       fields.Date.today())]).mapped('qty_done'))-sum(self.env['stock.move.line'].search([('product_id', '=', product_id),('location_id.warehouse_id','=',self.branch.id),
                                                                      ('date', '<',
                                                                       fields.Date.today())]).mapped('qty_done'))

        return (month1+month2+month3+month4+month5+month6+month7+month8+month9+month10+month11+month12)/12

    def get_qgs(self,product_id):
        return sum(self.env['sale.order.line'].search([('wareh','=',self.branch.id),('qty_invoiced','!=',0),('product_id','=',product_id)]).mapped('qty_invoiced'))

class pharma_price_list(models.TransientModel):
    _name = 'droga.pharma.itr.detail'
    header = fields.Many2one('droga.pharma.itr')
    product=fields.Many2one('product.template',string='Product')
    cogs=fields.Float('QOGS')
    av_inv=fields.Float('Avg.inv.Qty.')
    inv_tur=fields.Float('ITR')
    dsi = fields.Float('Days to sell')

