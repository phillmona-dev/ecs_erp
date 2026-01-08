from odoo import models, fields, api
from odoo.tools.sql import drop_view_if_exists
from datetime import datetime


class PaymentReport(models.Model):
    _name = 'droga.finance.payment.report'

    _auto = False

    id = fields.Integer('Id')
    partner_id = fields.Many2one("res.partner")
    payment_type = fields.Char("Payment Type")
    category = fields.Char("Customer Category")
    division = fields.Char("Division")
    sales_channel = fields.Char("Sales Channel")
    invoice_no = fields.Char("Invoice")
    sales_type = fields.Char("Sales Type")
    sales_initiator = fields.Char("Sales Initiator")
    invoice_date_due = fields.Date("Due Date")
    paid_date = fields.Date("Paid Date")
    total_amount = fields.Float("Total Amount")
    paid_amount = fields.Float("Paid Amount")
    settled_amount = fields.Float("Settled Amount")
    due_days = fields.Integer("Due Days")
    paid_passed_days = fields.Integer("Paid Passed Days")
    # payment_id = fields.Many2one("account.payment")
    # move_id = fields.Many2one("account.move")
    company_id = fields.Many2one("res.company")

    def compute_sales_info(self):
        for record in self:
            record.category = ""
            record.division = ""
            record.sales_channel = ""
            if record.payment_type == 'Customer':
                # get customer category
                record.category = 'Others'
                record.division = "Others"
                record.sales_channel = "Marketing"
                record.category = record.partner_id.cust_type_ext.cust_org_type

                # search account move
                account_move = self.env["account.move"].sudo().search([('name', '=', record.invoice_no)])
                for o in account_move.invoice_line_ids:
                    if o.analytic_distribution:
                        analytic_distributions = o.analytic_distribution
                        for analytic_distribution_id in analytic_distributions:
                            # search analytic definition table
                            analytic_plans = self.env['account.analytic.account'].search(
                                [('id', '=', analytic_distribution_id)])
                            for analytic_plan in analytic_plans:
                                if analytic_plan.plan_id.complete_name == 'Profit / Cost Center':
                                    record.division = analytic_plan.display_name
                                elif analytic_plan.plan_id.complete_name == 'Sales Channel':
                                    record.sales_channel = analytic_plan.display_name
                        break

    def init(self):
        cr = self.env.cr

        # Drop any existing view or materialized view safely
        cr.execute("""
               DROP MATERIALIZED VIEW IF EXISTS droga_finance_payment_report CASCADE;
               DROP VIEW IF EXISTS droga_finance_payment_report CASCADE;
           """)

        # Create the materialized view with row_number()
        cr.execute("""
               CREATE MATERIALIZED VIEW droga_finance_payment_report AS
               SELECT
                   row_number() OVER () AS id,
                   ap.id AS payment_id,
                   am.id AS move_id,
                   am.company_id,
                   ap.partner_id,
                   CASE
                       WHEN ap.payment_type = 'inbound' THEN 'Customer'
                       ELSE 'Vendor'
                   END AS payment_type,
                   ap.category,
                   ap.division,
                   ap.sales_channel,
                   am.name AS invoice_no,
                   am.sales_type,
                   am.sales_initiator,
                   am.invoice_date_due,
                   apr.max_date AS paid_date,
                   CASE
                       WHEN ap.payment_type = 'inbound' THEN am.amount_total_signed
                       ELSE abs(am.amount_total_signed)
                   END AS total_amount,
                   ap.amount AS paid_amount,
                   apr.amount AS settled_amount,
                   (apr.max_date - am.invoice_date_due) AS due_days,
                   (CURRENT_DATE - apr.max_date) AS paid_passed_days
               FROM account_move am
               JOIN account_move_line aml
                   ON aml.move_id = am.id
                  AND aml.display_type = 'payment_term'
               JOIN account_partial_reconcile apr
                   ON apr.debit_move_id = aml.id
                   OR apr.credit_move_id = aml.id
               JOIN account_move_line pml
                   ON (pml.id = apr.credit_move_id OR pml.id = apr.debit_move_id)
                  AND pml.payment_id IS NOT NULL
               JOIN account_payment ap
                   ON ap.id = pml.payment_id
               WHERE am.state = 'posted';
           """)

        # Create supporting indexes for performance
        cr.execute("""
        
                CREATE UNIQUE INDEX idx_dfpr_id
                ON droga_finance_payment_report (id);
        
               CREATE INDEX idx_dfpr_partner
               ON droga_finance_payment_report (partner_id);

               CREATE INDEX idx_dfpr_company
               ON droga_finance_payment_report (company_id);

               CREATE INDEX idx_dfpr_paid_date
               ON droga_finance_payment_report (paid_date);
           """)

    @api.model
    def refresh_payment_report(self):
        """
        Refresh materialized view without blocking users
        """
        self.env.cr.execute("""
                REFRESH MATERIALIZED VIEW CONCURRENTLY droga_finance_payment_report;
            """)


class AccountPaymentLinK(models.Model):
    _name = 'droga.account.payment.link'

    _auto = False

    id = fields.Integer('Id')
    payment_id = fields.Many2one("account.payment")
    move_id = fields.Many2one("account.move")
    payment_move_id = fields.Many2one("account.move")
    name = fields.Char("Name")

    def init(self):
        drop_view_if_exists(self.env.cr, 'droga_account_payment_link')
        self.env.cr.execute("""
                               create or replace view droga_account_payment_link as (

                                    select row_number()over() as id,payment_id,move_id,payment_move_id,(select name from account_move where id=x.payment_move_id ) as name from(
                                select ap.id as payment_id,aml.move_id,ap.move_id as payment_move_id
                                from account_move am 
                                inner join account_move_line aml on  am.id=aml.move_id 
                                inner join account_partial_reconcile apr on aml.id=apr.debit_move_id 
                                inner join account_payment ap on ap.id=(select distinct payment_id  from account_move_line   where id=apr.credit_move_id)
                                where aml.display_type ='payment_term' and ap.payment_type='inbound' 
                                
                                
                                union 
                                
                                select ap.id as payment_id,aml.move_id,ap.move_id as payment_move_id
                                from account_move am 
                                inner join account_move_line aml on  am.id=aml.move_id 
                                inner join account_partial_reconcile apr on aml.id=apr.credit_move_id  
                                inner join account_payment ap on ap.id=(select distinct payment_id  from account_move_line   where id=apr.debit_move_id)
                                where aml.display_type ='payment_term' and ap.payment_type='outbound')x

                               )""")


class AccountPaymentLinkTable(models.Model):
    _name = "droga.account.payment.link.data"

    payment_id = fields.Many2one("account.payment")
    move_id = fields.Many2one("account.move")
    move_line_id = fields.Many2one("account.move.line")
    payment_move_id = fields.Many2one("account.move")
    name = fields.Char("Name")
