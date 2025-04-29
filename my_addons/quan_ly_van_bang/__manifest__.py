# -*- coding: utf-8 -*-

{
    'name': 'Quản lý văn bằng',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'QLVB Module',
    'description': """
        QLVB Module
    """,
    'author': 'D24 Team',
    'depends': ['base'],
    'data': [

        'views/student_view.xml',
        'views/certificate_view.xml',
        'menu_view.xml',
    ],
    'installable': True,
    'application': True,
}