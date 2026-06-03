# -*- coding: utf-8 -*-
{
    'name': 'ECS Construction',
    'version': '19.0.1.0.0',
    'summary': 'Company B (Construction) specialization layer',
    'description': """
        Handles specialized workflows for Company B:
        - Project management extensions (site foreman, engineer)
        - Bill of Quantities (BOQ) tracking per project task/material
        - Customer and Subcontractor Contracts management
        - Progress billing (work valuation certificates) with automated retention checks and Odoo invoice generation
        - Company-scoped records isolation
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Operations',
    'depends': [
        'project',
        'stock',
        'account',
        'ecs_base',
        'ecs_finance',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/default_admin_groups.xml',
        'views/project_views.xml',
        'views/boq_views.xml',
        'views/contract_views.xml',
        'views/progress_billing_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
