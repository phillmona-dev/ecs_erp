# -*- coding: utf-8 -*-
{
    'name': 'ECS Inventory',
    'version': '19.0.1.0.0',
    'summary': 'Multi-company inventory controls for ECS ERP',
    'description': """
        Inventory foundation module for ECS Multi-Company ERP.
        Provides:
        - Standardized inventory transaction types
        - Company-scoped inventory lock periods
        - Stock picking classification and locked-period validation
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Inventory',
    'depends': [
        'stock',
        'stock_account',
        'product_expiry',
        'hr',
        'mail',
        'ecs_base',
        'ecs_approvals',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/default_admin_groups.xml',
        'views/inventory_request_views.xml',
        'views/inventory_transaction_type_views.xml',
        'views/inventory_lock_period_views.xml',
        'views/stock_picking_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
