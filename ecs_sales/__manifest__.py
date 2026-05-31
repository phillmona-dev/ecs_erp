# -*- coding: utf-8 -*-
{
    'name': 'ECS Sales',
    'version': '18.0.1.0.0',
    'summary': 'Multi-company sales management — credit limits and discount rules',
    'description': """
        Sales management module for ECS Multi-Company ERP.
        Provides:
        - Customer credit limit tracking (unsettled amount, available balance)
        - Credit limit checks on Sale Order validation based on payment terms
        - Block sales if customer has matured (overdue) unpaid invoices
        - Multi-company discount rules engine (Customer/Category/Product/Payment Term discount)
        - Company-scoped record rules for isolation
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Sales',
    'depends': [
        'sale',
        'ecs_base',
        'ecs_finance',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/partner_views.xml',
        'views/payment_term_views.xml',
        'views/sale_order_views.xml',
        'views/discount_rule_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
