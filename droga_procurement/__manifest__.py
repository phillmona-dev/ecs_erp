# -*- coding: utf-8 -*-
{
    'name': "Droga Procurement",

    'summary': """
       Local and Foreign Purchase Management""",

    'description': """
        Local and Foreign Purchase Management
    """,

    'author': "Afomsoft Technologies",
    'website': "https://afomsoft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory/Purchase',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase', 'stock','web_studio'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/procurement_security.xml',
        'views/purchase_order.xml',
        'views/purchase_request.xml',

        'views/rfq.xml',
        'views/purchase_foregin_status.xml',
        'views/configuration.xml',
        'report/paper_format.xml',
        'report/purchase_request.xml',
        'report/rfq.xml',
        'views/menu.xml',

    ],
    # only loaded in demonstration mode
    'demo': [

    ],

    'installable': True,
    'application': True,
}
