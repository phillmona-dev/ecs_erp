# -*- coding: utf-8 -*-
{
    'name': 'ECS Finance',
    'version': '19.0.1.0.0',
    'summary': 'Multi-company finance extension — withholding, payment requests, transaction types',
    'description': """
        Finance foundation module for ECS Multi-Company ERP.
        Provides:
        - Per-company withholding tax configuration (replaces hardcoded rates)
        - Per-company transaction type sequences (CPV, BPV, CRV, BRV, JV)
        - Payment Request multi-level approval workflow
        - Account Move extensions (amount-in-words, CRV, withholding state)
        - Account Payment extensions (check printing, transaction numbering)
        - Security groups: Finance Manager, Accountant, Budget Controller, Cashier, Viewer
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Finance',
    'depends': [
        'account',
        'mail',
        'ecs_base',
        'ecs_approvals',
        'hr',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ecs_finance_data.xml',
        'views/withholding_config_views.xml',
        'views/transaction_type_views.xml',
        'views/payment_request_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/menu.xml',
        'report/payment_voucher_report.xml',
        'report/crv_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
