from odoo import models, fields, api
from odoo.exceptions import UserError


class droga_date_change(models.Model):
    _name='droga.date.change'
    reference=fields.Many2one('stock.picking',required=True)
    transaction_date=fields.Datetime(string='From date',compute='get_date',store=True)
    new_transaction_date=fields.Date('Transaction date correct')
    status=fields.Selection([('Draft','Draft'),('Processed','Processed')],default='Draft')
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 index=True, default=lambda self: self.env.company.id)

    @api.depends('reference')
    def get_date(self):
        for rec in self:
            if rec.status=='Draft':
                rec.transaction_date=rec.reference.date_done

    def update_date(self):
        if not self.new_transaction_date:
            raise UserError("Date can not be empty.")

        if self.new_transaction_date <= self.company_id.tax_lock_date:
            raise UserError("Tax period is closed for the stated period. Latest period transaction can be adjusted is "+str(self.company_id.tax_lock_date))

        done_moves=self.env['stock.move'].search([('picking_id','=',self.reference.id)])
        self.status='Processed'
        self.reference.date_done = self.new_transaction_date
        #self.reference.date = self.new_transaction_date
        for mv in done_moves:
            for mvl in mv.move_line_ids:
                mvl.date=self.new_transaction_date
            mv.date = self.new_transaction_date
            stock_layers=self.env['droga.stock.valuation.layer'].search([('stock_move_id','=',mv.id)])
            for layer in stock_layers:
                layer.move_date=self.new_transaction_date

                query1 = """
                            update account_move set company_id=6 where id=%s
                        """
                self.env.cr.execute(query1, (
                    layer.account_move_id.id,))

                query2 = """
                            update account_move_line set company_id=6 where move_id=%s
                        """

                self.env.cr.execute(query2, (
                    layer.account_move_id.id,))

                layer.account_move_id = False

                layer.update_wa_after_date(layer)
