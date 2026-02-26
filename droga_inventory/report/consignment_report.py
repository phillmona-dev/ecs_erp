import calendar

from odoo import models, fields, api
from odoo.http import request


class droga_crm_grade_vs_schedule(models.Model):
    _name='droga.inventory.consignment.report'
    _auto = False

    customer_name=fields.Char('Customer')
    company_id = fields.Many2one('res.company', 'Company ID')
    name=fields.Char('Name')
    state=fields.Char('State')
    consid=fields.Char('Consignment ID')
    type = fields.Char('Type')
    store_reference=fields.Char('Store reference')
    tender_origin=fields.Char('Tender origin')
    sales_order = fields.Char('Sales order')
    trans_date = fields.Date('Date')
    req_user=fields.Char('Requesting user')

    def _table_exists(self, table_name):
        self.env.cr.execute(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM information_schema.tables
                 WHERE table_schema = 'public'
                   AND table_name = %s
            )
            """,
            (table_name,),
        )
        return bool(self.env.cr.fetchone()[0])

    def _column_exists(self, table_name, column_name):
        self.env.cr.execute(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = %s
                   AND column_name = %s
            )
            """,
            (table_name, column_name),
        )
        return bool(self.env.cr.fetchone()[0])

    def open_cons(self):
        if self.name.startswith('CON/ISSUE'):
            return {
                'name': 'Consignment/sample issues',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'droga.inventory.consignment.issue',
                'type': 'ir.actions.act_window',
                'res_id': self.consid,
            }
        else:
            return {
                'name': 'Consignment/sample receipts',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'droga.inventory.consignment.receive',
                'type': 'ir.actions.act_window',
                'res_id': self.consid,
            }

    def init(self):
        tender_origin_expr = "' '"
        if self._table_exists('droga_tender_master') and self._column_exists(
            'droga_inventory_consignment_issue', 'tender_origin_form'
        ):
            tender_origin_expr = (
                "(select y.ten_id from droga_tender_master y "
                "where y.id=droga_inventory_consignment_issue.tender_origin_form)"
            )

        issue_sales_order_expr = "' '"
        issue_sales_order_conditions = []
        if self._table_exists('sale_order'):
            if self._column_exists('droga_inventory_consignment_issue', 'subcontract_issue_origin_form'):
                issue_sales_order_conditions.append(
                    "y.id=droga_inventory_consignment_issue.subcontract_issue_origin_form"
                )
            if self._column_exists('droga_inventory_consignment_issue', 'bag_issue_order'):
                issue_sales_order_conditions.append(
                    "y.id=droga_inventory_consignment_issue.bag_issue_order"
                )
        if issue_sales_order_conditions:
            issue_sales_order_expr = (
                "(select y.name from sale_order y where "
                + " or ".join(issue_sales_order_conditions)
                + ")"
            )

        receive_sales_order_expr = "' '"
        if self._column_exists('droga_inventory_consignment_receive', 'subcontractor_return_origin_form'):
            receive_sales_order_expr = (
                "(select y.name from droga_inventory_consignment_issue y "
                "where y.id=droga_inventory_consignment_receive.subcontractor_return_origin_form)"
            )

        issue_req_user_expr = "' '"
        if self._column_exists('droga_inventory_consignment_issue', 'user_id_des'):
            issue_req_user_expr = "droga_inventory_consignment_issue.user_id_des"
        elif self._column_exists('droga_inventory_consignment_issue', 'user_id'):
            issue_req_user_expr = "CAST(droga_inventory_consignment_issue.user_id AS VARCHAR)"

        receive_req_user_expr = "' '"
        if self._column_exists('droga_inventory_consignment_receive', 'user_id_des'):
            receive_req_user_expr = "droga_inventory_consignment_receive.user_id_des"
        elif self._column_exists('droga_inventory_consignment_receive', 'user_id'):
            receive_req_user_expr = "CAST(droga_inventory_consignment_receive.user_id AS VARCHAR)"

        self.env.cr.execute(f""" 
           create or replace view droga_inventory_consignment_report as 
           (
                select row_number() over () as id,g.* from (
                select (select y.name from res_partner y where y.id=droga_inventory_consignment_issue.customer) as customer_name,company_id,name,
case state when 'draft' then 'Draft' when 'cancel' then 'Cancelled' when 'stmg' then 'Store manager' when 'mg' then 'Export manager'
when 'waiting' then 'Requested' when 'sc' then 'Sent to CU' when 'reject' then 'Rejected' when 'processed' then 'Processed'
when 'pmg' then 'Project Engineer' end as state,issue_date as trans_date,id as consid,
case issue_type when 'CONI' then 'Consignment' when 'INC' then 'Internal consumption' when 'PRI' then 'Project internal' when 'PRC' then 'Project contractor'
when 'SIF' then 'Free sample' when 'SIR' then 'Sample issue to be returned' when 'SAP' then 'Free sample' when 'SUBL' then 'Cleaning unit issue' when 'BAGI' then 'Bag issue order' end as type
,consignment_reference as store_reference,{tender_origin_expr} as tender_origin 
,{issue_sales_order_expr} as sales_order,{issue_req_user_expr} as req_user from droga_inventory_consignment_issue

union

select (select y.name from res_partner y where y.id=droga_inventory_consignment_receive.supplier) as customer_name,company_id,name,
case state when 'draft' then 'Draft' when 'cancel' then 'Cancelled' when 'done' then 'Processed' when 'stmg' then 'Store manager' when 'mg' then 'Export manager' when 'mtmg' then 'Marketting manager'
when 'waiting' then 'Requested' when 'sc' then 'Sent to CU' when 'reject' then 'Rejected' when 'processed' then 'Processed'
when 'pmg' then 'Project Engineer' end as state,receipt_date as trans_date,id as consid,
case issue_type when 'CONR' then 'Consignment recieve' when 'INC' then 'Internal consumption' when 'PRI' then 'Project internal' when 'PRC' then 'Project contractor'
when 'SIF' then 'Free sample' when 'SAR' then 'Sample issue to be returned' when 'SIR' then 'Sample issue to be returned' when 'SUBL' then 'Cleaning unit issue' when 'BAGI' then 'Bag issue order' end as type
,consignment_reference as store_reference,' ' as tender_origin 
,{receive_sales_order_expr} as sales_order,{receive_req_user_expr} as req_user from droga_inventory_consignment_receive) g
           )
        """)
