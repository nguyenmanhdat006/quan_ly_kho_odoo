from odoo import models, fields, api

class NhanVien(models.Model):
    _name = 'nhan.vien'
    _description = 'Nhân viên'

    ma_nhan_vien = fields.Char(string='Mã nhân viên', readonly=True, copy=False)
    ten_nv = fields.Char(string='Tên nhân viên', required=True)
    gioi_tinh = fields.Selection([
        ('nam', 'Nam'),
        ('nu', 'Nữ'),
        ('khac', 'Khác')
    ], string='Giới tính', required=True)
    dia_chi = fields.Text(string='Địa chỉ')
    so_dien_thoai = fields.Char(string='Số điện thoại')
    vai_tro = fields.Selection([
        ('ke_toan', 'Kế toán'),
        ('nhan_vien_kho', 'Nhân viên kho'),
        ('lao_cong', 'Lao công'),
        # Thêm các vai trò khác nếu cần
    ], string='Vai trò')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'ma_nhan_vien' in fields_list:
            res['ma_nhan_vien'] = self.env['ir.sequence'].next_by_code('nhan.vien') or '/'
        return res