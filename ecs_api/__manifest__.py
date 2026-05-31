# -*- coding: utf-8 -*-
{
    'name': 'ECS API',
    'version': '18.0.1.0.0',
    'summary': 'REST API Endpoints for external integrations (attendance devices, mobile)',
    'description': """
        Exposes secure RESTful JSON-RPC/JSON endpoints for multi-company ECS ERP:
        - `/api/v1/attendance/push` — For biometric/attendance machines to push check-in/check-out logs.
        - `/api/v1/employee/profile` — Quick read of profile and basic directory info.
        - Security token validation using simple system parameters.
    """,
    'author': 'phillipos1212@gmail.com',
    'website': 'https://my-portfolio-jk3j.onrender.com/',
    'category': 'ECS/API',
    'depends': [
        'ecs_base',
        'ecs_hr',
    ],
    'data': [
        'data/ir_config_parameter_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
