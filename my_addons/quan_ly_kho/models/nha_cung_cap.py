from odoo import models, fields, api

class NhaCungCap(models.Model):
    _name = 'nha.cung.cap'
    _description = 'Nhà cung cấp'

    ma_ncc = fields.Char(string='Mã nhà cung cấp', readonly=True, copy=False)
    ten_ncc = fields.Char(string='Tên nhà cung cấp', required=True)
    dia_chi = fields.Text(string='Địa chỉ')
    so_dien_thoai = fields.Char(string='Số điện thoại')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'ma_ncc' in fields_list:
            res['ma_ncc'] = self.env['ir.sequence'].next_by_code('nha.cung.cap') or '/'
        return res
