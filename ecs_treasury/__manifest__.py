# -*- coding: utf-8 -*-
{
    'name': 'ECS Treasury',
    'version': '18.0.1.0.0',
    'summary': 'Treasury controls for ECS ERP',
    'description': """
        Treasury foundation for ECS ERP.
        Provides company-scoped treasury facilities and repayment schedules.
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Treasury',
    'depends': [
        'account',
        'mail',
        'ecs_base',
        'ecs_finance',
        'ecs_approvals',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/treasury_facility_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
