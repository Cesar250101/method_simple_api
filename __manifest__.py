# -*- coding: utf-8 -*-
{
    'name': "method_simple_api",

    'summary': """
        Integración Method ERP con SimpleAPI""",

    'description': """
        Integración para la emisión de documentos electronicos
    """,

    'author': "Method ERP",
    'website': "https://www.method.cl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','l10n_cl_fe','base_currency_inverse_rate','method_minori'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/compañia.xml',
        'views/templates.xml',
        'views/account_invoice.xml',
        'views/product_template.xml',
        'views/res_country.xml',
        'data/cron.xml',
        'wizard/apicaf.xml',
        'views/layout.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}