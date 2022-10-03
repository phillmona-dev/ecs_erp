from odoo import models,fields

class droga_awarded_tenders_view(models.Model):
    _name='droga.awarded.tenders.view'
    _auto = False

    cust_name=fields.Char('Customer name')
    award_folder_no=fields.Char('Award folder number')
    procurement_title=fields.Char('Procurement title')
    amt=fields.Float('Value')

    def init(self):
        self._cr.execute(""" 
           create or replace view droga_awarded_tenders_view as 
           (
                select row_number() over () as id,(select y.name from res_partner y where y.id=a.customer) as cust_name,
                (select y.award_fold_num from droga_tender_submission_detail y where y.parent_tender_submission=a.id limit 1) as award_folder_no,a.procurement_title as procurement_title,(select sum(y.amount) from droga_tender_submission_detail y 
                where y.status='awarded' and y.parent_tender_submission=a.id) as amt from droga_tender_master a
           )
        """)