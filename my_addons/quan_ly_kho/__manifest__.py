{
    'name': 'Quản lý kho',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Module quản lý kho',
    'description': """
        Module quản lý kho với các chức năng:
        - Quản lý nhân viên
        - Quản lý khách hàng
        - Quản lý nhà cung cấp
        - Quản lý sản phẩm
        - Quản lý kho
        - Quản lý phiếu nhập/xuất
        - Quản lý bộ phận
    """,
    'author': 'Nhóm 01',
    'depends': ['base'],
    'data': [
        'security/quan_ly_kho_groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/nhan_vien.xml',
        'views/khach_hang.xml',
        'views/nha_cung_cap.xml',
        'views/san_pham.xml',
        'views/kho.xml',
        'views/phieu_nhap.xml',
        'views/phieu_xuat.xml',
        'views/bo_phan_quan_ly.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}