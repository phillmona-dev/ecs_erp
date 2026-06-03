# -*- coding: utf-8 -*-
{
    'name': 'ECS Consolidated Report',
    'version': '19.0.1.0.0',
    'summary': 'Cross-company P&L, cash position, and KPI dashboard',
    'description': """
        Executive reporting layer for multi-company ECS ERP:
        - Cross-company Profit & Loss summary (reads from account.move.line)
        - Cash position per company (bank/cash journal balances)
        - Procurement KPIs: PR-to-PO lead time, open PRs, pending payments
        - HR KPIs: headcount by department and payroll cost
        - All reports are company-filter-aware
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Reporting',
    'depends': [
        'account',
        'ecs_base',
        'ecs_finance',
        'ecs_hr',
        'ecs_payroll',
        'ecs_procurement',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/consolidated_pl_views.xml',
        'views/cash_position_views.xml',
        'views/kpi_dashboard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
