# -*- coding: utf-8 -*-
{
    'name': "Droga Inventory",

    'summary': """
        Droga Pharma Pvt. Ltd.Co Inventory module extension.""",

    'description': """
        This module is developed for Droga Pharma Pvt. Ltd.Co. It works as an extension module to handle inventory operations. 
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Inventory',
    'version': '1.0',

    # always loaded
    'data': [
        'security/security.xml',
        'security/record_rules.xml',
        'views/module_menus.xml',
        'data/droga_inv_sequence.xml',
        'security/ir.model.access.csv',
        'views/droga_stock_transfer_custom.xml',
        'views/droga_stock_consignment_receipt.xml',
        'views/droga_stock_consignment_issue.xml',
        'views/droga_stock_extensions.xml',
        'views/droga_stock_product_extension.xml',
        'views/droga_stock_office_supplies_request.xml',
        'report/report_tree_extension.xml',
        'report/xls_stock_card.xml',
        'report/store_request.xml',
    ],

    # any module necessary for this one to work correctly

    'depends': ['base',
                'mail',
                'resource','droga_procurement',
                'web', 'crm'],
    "license": "AGPL-3",
    # only loaded in demonstration mode
    'installable': True,
    'application': True
}
