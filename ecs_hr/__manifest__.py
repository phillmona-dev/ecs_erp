# -*- coding: utf-8 -*-
{
    'name': 'ECS HR',
    'version': '19.0.1.0.0',
    'summary': 'Multi-company HR — employees, attendance, overtime, headcount',
    'description': """
        HR foundation module for ECS Multi-Company ERP.
        Provides:
        - Employee extensions: Amharic name, TIN, pension, Ethiopian retirement age (60)
        - Employee ID auto-generation via ecs.sequence.service
        - Biometric attendance integration with duplicate check prevention
        - Real worked hours (Ethiopian standard: -1hr break deduction)
        - Attendance Report model with company isolation
        - Overtime Report with ecs.approval.mixin workflow
        - HR Division / Business Unit model (per company)
        - Headcount Request workflow
        - HR Letter generation
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/HR',
    'depends': [
        'hr',
        'hr_attendance',
        'mail',
        'ecs_base',
        'ecs_approvals',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/default_admin_groups.xml',
        'views/employee_views.xml',
        'views/hr_division_views.xml',
        'views/attendance_views.xml',
        'views/overtime_views.xml',
        'views/headcount_views.xml',
        'views/hr_letter_views.xml',
        'views/menu.xml',
        'report/attendance_report.xml',
        'report/overtime_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
