from odoo import models, fields, api

class SanPham(models.Model):
    _name = 'san.pham'
    _description = 'Sản phẩm'

    ma_san_pham = fields.Char(string='Mã sản phẩm', readonly=True, copy=False)
    ten_san_pham = fields.Char(string='Tên sản phẩm', required=True)
    xuat_xu = fields.Char(string='Xuất xứ')
    so_luong = fields.Integer(string='Số lượng')
    gia_nhap = fields.Float(string='Giá nhập')
    gia_ban = fields.Float(string='Giá bán')
    ngay_san_xuat = fields.Date(string='Ngày sản xuất')
    han_su_dung = fields.Date(string='Hạn sử dụng')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'ma_san_pham' in fields_list:
            res['ma_san_pham'] = self.env['ir.sequence'].next_by_code('san.pham') or '/'
        return res