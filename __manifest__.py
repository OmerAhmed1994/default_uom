# -*- coding: utf-8 -*-
{
    'name': 'Default UOM',
    'version': '1.0',
    'category': 'Stuck',
    'sequence': 6,
    'author': 'Omer Ahmed',
    'summary': """
        module allows you to use default UOM 
    """ ,
    'description': """
        module allows you to use default UOM 
    """,
    'depends': ['stock', 'account', 'sale_management', 'purchase_stock'],
    'data': [
        'views/views.xml',
    ],
    'installable': True,
    'application': False,
    'website': '',
    'auto_install': False,
}
