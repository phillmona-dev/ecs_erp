# -*- coding: utf-8 -*-
{
    'name': 'ECS Procurement',
    'version': '18.0.1.0.0',
    'summary': 'Multi-company procurement foundation for ECS ERP',
    'description': """
        Procurement foundation module for ECS Multi-Company ERP.
        Provides:
        - Local and foreign purchase requests
        - Company-scoped procurement approval workflow
        - Purchase request lines with estimated amounts
        - Conversion of approved requests to draft purchase orders
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Procurement',
    'depends': [
        'purchase',
        'stock',
        'hr',
        'mail',
        'ecs_base',
        'ecs_approvals',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/purchase_request_views.xml',
        'views/purchase_rfq_views.xml',
        'views/import_tracking_views.xml',
        'views/purchase_order_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
