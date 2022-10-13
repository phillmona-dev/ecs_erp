# -*- coding: utf-8 -*-
{
    'name': "Droga CRM",

    'summary': """
        Droga Pharma Pvt. Ltd.Co CRM extension module.""",

    'description': """
        This module is developed for Droga Pharma Pvt. Ltd.Co. It works as an extension for CRM module.
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'CRM Extension',
    'version': '1.0',

    # always loaded
    'data': [
        'views/cust_extension.xml',
        'views/customer_visits.xml',
        'views/doctors_schedule.xml',
        'views/cust_grade.xml',
        'views/settings/region.xml',
        'views/settings/city.xml',
        'views/settings/area.xml',
        'views/settings/location.xml',
        'views/settings/sub_location.xml',
    ],

    # any module necessary for this one to work correctly

    'depends': ['base','hr',
                'mail',
                'resource',
                'web', 'crm'],
    "license": "AGPL-3",
    # only loaded in demonstration mode
    'installable': True,
    'application': True
}
