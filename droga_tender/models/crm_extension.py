from odoo import models, fields, api


class tender_customer_extension(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals_list):
        new_cus=super().create(vals_list)
        if 'customer_rank' in vals_list:
            if vals_list["customer_rank"]>0 and vals_list["is_company"]:
                prev_rec=self.env['droga.tender.settings.customers'].search([('name','=',vals_list['name'])])
                if len(prev_rec)>0:
                    for rec in prev_rec:
                        rec['master_cust_id']=new_cus.id
                        rec['customer_type']=vals_list['cust_type_ext']
                else:
                    tender_cus={
                        'name':vals_list['name'],
                        'master_cust_id':new_cus.id,
                        'customer_type':vals_list['cust_type_ext']}
                    self.env['droga.tender.settings.customers'].create(tender_cus)

        return new_cus