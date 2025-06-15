from odoo import models, fields, api

class KhachHang(models.Model):
    _name = 'khach.hang'
    _description = 'Khách hàng'

    ma_khach_hang = fields.Char(string='Mã khách hàng', readonly=True, copy=False)
    ten = fields.Char(string='Tên khách hàng', required=True)
    dia_chi = fields.Text(string='Địa chỉ')
    so_dien_thoai = fields.Char(string='Số điện thoại')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'ma_khach_hang' in fields_list:
            res['ma_khach_hang'] = self.env['ir.sequence'].next_by_code('khach.hang') or '/'
        return res
