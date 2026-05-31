# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class EcsKpiDashboard(models.TransientModel):
    """
    KPI Dashboard Wizard for Multi-Company ECS ERP.
    Calculates essential Procurement & HR metrics.
    """
    _name = 'ecs.kpi.dashboard'
    _description = 'ECS KPI Dashboard'

    name = fields.Char(string='Dashboard', default='Executive KPI Summary')
    company_ids = fields.Many2many(
        'res.company', string='Companies', required=True,
        default=lambda self: self.env.companies
    )
    
    # ── Procurement KPIs ──────────────────────────────────────────────
    avg_pr_to_po_lead_time = fields.Float(
        string='Avg. PR to PO Lead Time (Days)', readonly=True,
        help="Average time from Purchase Request creation to PO confirmation."
    )
    pending_pr_count = fields.Integer(string='Pending Purchase Requests', readonly=True)
    open_rfq_count = fields.Integer(string='Open RFQs', readonly=True)

    # ── HR & Payroll KPIs ──────────────────────────────────────────────
    total_headcount = fields.Integer(string='Total Headcount', readonly=True)
    monthly_payroll_cost = fields.Monetary(string='Current Month Payroll Cost', currency_field='company_currency_id', readonly=True)
    avg_overtime_hours = fields.Float(string='Average Monthly Overtime Hours per Employee', readonly=True)
    
    company_currency_id = fields.Many2one(
        'res.currency', string='Display Currency',
        default=lambda self: self.env.company.currency_id
    )

    def action_calculate_kpis(self):
        self.ensure_one()
        
        # 1. Total Headcount
        employees = self.env['hr.employee'].search([
            ('company_id', 'in', self.company_ids.ids),
            ('active', '=', True)
        ])
        headcount = len(employees)

        # 2. Monthly Payroll Cost (Sum of last 30 days payslips)
        payslips = self.env.get('hr.payslip') and self.env['hr.payslip'].search([
            ('company_id', 'in', self.company_ids.ids),
            ('state', '=', 'done')
        ])
        # Simple convert loop
        pay_cost = 0.0
        for payslip in payslips:
            pay_cost += payslip.company_id.currency_id._convert(
                payslip.net_wage, self.company_currency_id, self.env.company, fields.Date.today()
            )

        # 3. Pending Purchase Requests (Draft, Submitted states)
        pending_pr = self.env['ecs.purchase.request'].search_count([
            ('company_id', 'in', self.company_ids.ids),
            ('state', 'in', ('draft', 'submitted'))
        ])

        # 4. Open RFQs
        open_rfqs = self.env['purchase.order'].search_count([
            ('company_id', 'in', self.company_ids.ids),
            ('state', 'in', ('draft', 'sent'))
        ])

        # 5. Calculate Average Lead Time (Purchase Request creation -> PO confirmation)
        purchase_orders = self.env['purchase.order'].search([
            ('company_id', 'in', self.company_ids.ids),
            ('state', 'in', ('purchase', 'done')),
            ('ecs_purchase_request_id', '!=', False),
        ])

        lead_times = []
        for order in purchase_orders:
            po_date = order.date_approve
            pr_date = order.ecs_purchase_request_id.create_date
            if po_date and pr_date:
                delta = (po_date - pr_date).days
                lead_times.append(max(0, delta))
                
        avg_lead = sum(lead_times) / len(lead_times) if lead_times else 0.0

        # 6. Average overtime hours from ECS HR overtime logs
        overtimes = self.env['ecs.hr.overtime'].search([
            ('company_id', 'in', self.company_ids.ids),
            ('state', '=', 'approved')
        ])
        tot_ot_hours = sum(overtimes.mapped('overtime_hours'))
        avg_ot = tot_ot_hours / headcount if headcount > 0 else 0.0

        self.write({
            'avg_pr_to_po_lead_time': avg_lead,
            'pending_pr_count': pending_pr,
            'open_rfq_count': open_rfqs,
            'total_headcount': headcount,
            'monthly_payroll_cost': pay_cost,
            'avg_overtime_hours': avg_ot
        })

        return {
            'name': _('Executive KPI Dashboard'),
            'type': 'ir.actions.act_window',
            'res_model': 'ecs.kpi.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new'
        }
