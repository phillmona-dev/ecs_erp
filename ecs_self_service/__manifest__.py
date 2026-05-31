# -*- coding: utf-8 -*-
{
    'name': 'ECS Employee Self Service',
    'version': '18.0.1.0.0',
    'summary': 'Single-entry portal for employee requests and approvals',
    'description': """
        Exposes a unified Employee Self Service menu:
        - View and create My Purchase Requests (restricted to creator)
        - View and create My Payment Requests (restricted to creator)
        - View and create My Store Requisitions / Office Supplies (restricted to creator)
        - View and create My Head Count Requests (restricted to creator)
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/SelfService',
    'depends': [
        'ecs_base',
        'ecs_finance',
        'ecs_hr',
        'ecs_inventory',
        'ecs_procurement',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/actions.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
