# -*- coding: utf-8 -*-
{
    'name': "Droga Pharmacy Chain",

    'summary': """
        Droga Pharma Pvt. Ltd.Co Pharmacy project stand-alone module.""",

    'description': """
        This module is developed for Droga Pharma Pvt. Ltd.Co. The module contains cross-modular functionalities for inventory, finance, sales, PO and others as well.
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Pharmacy Extension',
    'version': '1.0',

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/droga_export_emp_extension.xml',
        'views/droga_physio_sales.xml',
        'views/droga_pharmacy_sales.xml',
        'reports/daily_sales.xml',
        'views/droga_physio_list.xml',
        'views/customers.xml',
        'views/children.xml',
        'views/rewards/droga_pharma_reward_gain_settings.xml',
        'views/rewards/droga_pharma_breast_feed_cont_type.xml',
        'views/rewards/droga_pharma_reward_issue_settings.xml',
        'views/rewards/droga_pharma_referral_gain_settings.xml',
        'views/rewards/droga_pharma_higher_value_settings.xml',
        'views/inventory/droga_pharma_inventory_menus.xml'
    ],

    # any module necessary for this one to work correctly

    'depends': ['base', 'hr', 'droga_sales',
                'mail', 'stock', 'http_routing', 'sale',
                'resource', 'stock', 'droga_inventory',
                'web', 'crm'],
    "license": "AGPL-3",
    # only loaded in demonstration mode
    'installable': True,
    'application': True,
}
