from odoo import models,fields
class customers_contacts_schedule(models.Model):
    _name='droga.crm.customers.contacts.view'
    _auto=False

    id=fields.Integer('id')
    cust_id=fields.Integer('Customer ID')
    cont_id = fields.Integer('Contact ID')
    cust_name=fields.Char('Customer name')
    cust_area = fields.Char('Customer area')
    cont_name = fields.Char('Contact name')
    day = fields.Char('Day')
    day_int = fields.Integer('Day int')
    time_from = fields.Float('Time from (ETH)')
    time_to = fields.Float('Time to (ETH)')

    def init(self):
        self._cr.execute(
            """create or replace view droga_crm_customers_contacts_view as 
            (select row_number() over() as id,
            a.day as day_int,(select m.area_name from droga_crm_settings_area m where m.id=(select g.area from res_partner g where g.id=(select y.parent_id from res_partner y where y.id=a.parent_customer_id))) as cust_area,
            (select g.name from res_partner g where g.id=(select y.parent_id from res_partner y where y.id=a.parent_customer_id)) as cust_name,
            (select y.parent_id from res_partner y where y.id=a.parent_customer_id) as cust_id,
            a.parent_customer_id as cont_id,(select y.name from res_partner y where y.id=a.parent_customer_id) as cont_name,
            case a.day when '0' then 'Monday' when '1' then 'Tuesday' when '2' then 'Wednesday' when '3' then 'Thrusday' when '4' then 'Friday' when '5' then 'Saturday' when '6' then 'Sunday' else 'Monday' end as day,
            a.time_from,a.time_to from droga_cust_contact_working_hours a)
            """
        )