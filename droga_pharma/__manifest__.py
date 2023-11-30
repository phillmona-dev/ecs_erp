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
        'views/dis_query_form.xml',
        'reports/mtm_report.xml',
        'reports/mtm_report_view.xml',
        'views/droga_physio_sales.xml',
        'views/droga_pharmacy_sales.xml',
        'reports/daily_sales.xml',
        'views/droga_physio_list.xml',
        'views/companies.xml',
        'views/children.xml',
        'views/rewards/droga_pharma_reward_gain_settings.xml',
        'views/rewards/droga_pharma_reward_issue_settings.xml',
        'views/rewards/droga_pharma_referral_gain_settings.xml',
        'views/rewards/droga_pharma_higher_value_settings.xml',
        'views/rewards/droga_pharma_breast_feed_cont_type.xml',
        'views/selection_settings/current_status.xml',
        'views/selection_settings/drug_theraphy_problems.xml',
        'views/selection_settings/drug_theraphy_cause.xml',
        'views/selection_settings/intervention.xml',
        'views/selection_settings/area_counsel.xml',
        'views/selection_settings/prod_categ.xml',
        'views/compounding.xml',
        'views/credit_limit_pharma.xml',
        'views/pcm/mtm.xml',
        'views/pcm/minor_alignment.xml',
        'views/pcm/counselling.xml',
        'views/pcm/follow_up_detail.xml',
        'views/inventory/product.xml',
        'reports/sales_report.xml',
        'reports/purchase_detail.xml',
        'reports/sales_detail_report.xml',
        'reports/inventory_report.xml',
        'views/menu.xml',
        'views/customers.xml',
        'views/inventory/droga_pharma_transfer_custom.xml',
        'views/inventory/location_extension.xml',
        'views/inventory/droga_pharma_inventory_menus.xml',
        'views/inventory/inventory_delivery_slip_extension.xml',
        'views/inventory/inter_pharmacy_transfer_custom.xml',
        'views/procurement_extension.xml'
    ],

    # any module necessary for this one to work correctly

    'depends': ['base', 'hr', 'droga_sales','droga_crm',
                'mail', 'stock', 'http_routing', 'sale',
                'resource', 'stock', 'droga_inventory',
                'web', 'crm'],
    "license": "AGPL-3",
    # only loaded in demonstration mode
    'installable': True,
    'application': True,
}
