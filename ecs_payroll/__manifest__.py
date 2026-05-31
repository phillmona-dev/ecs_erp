# -*- coding: utf-8 -*-
{
    'name': 'ECS Payroll',
    'version': '18.0.1.0.0',
    'summary': 'Multi-company payroll foundation for ECS ERP',
    'description': """
        Payroll foundation module for ECS Multi-Company ERP.
        Provides:
        - Ethiopian payroll contract allowances
        - Recurring employee payments and deductions
        - Variable payroll inputs by period
        - Company-scoped payroll rates
        - Payroll period configuration
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/Payroll',
    'depends': [
        'hr',
        'hr_contract',
        'mail',
        'ecs_base',
        'ecs_approvals',
        'ecs_hr',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/payroll_input_types.xml',
        'views/payroll_period_views.xml',
        'views/payroll_rate_views.xml',
        'views/payroll_tax_views.xml',
        'views/recurring_input_views.xml',
        'views/variable_input_views.xml',
        'views/hr_contract_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
