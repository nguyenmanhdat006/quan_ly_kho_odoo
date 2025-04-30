# -*- coding: utf-8 -*-

{
    "name": "Quản lý văn bằng",
    "version": "1.0",
    "category": "Tools",
    "summary": "QLVB Module",
    "description": """
        QLVB Module
    """,
    "author": "D24 Team",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/certificate_type_views.xml",
        "views/issuing_organization_views.xml",
        "views/certificate_application_views.xml",
        "views/certificate_status_logs_views.xml",
        "views/student_views.xml",
        "views/certificate_views.xml",
        "views/menu_access_control.xml",
        "views/qlvb_menus.xml",
        "data/sequence.xml",
    ],
    "installable": True,
    "application": True,
    "license": "AGPL-3",
}