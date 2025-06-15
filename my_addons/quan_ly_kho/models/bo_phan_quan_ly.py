from odoo import models, fields, api

class BoPhanQuanLy(models.Model):
    _name = 'bo.phan.quan.ly'
    _description = 'Bộ phận quản lý'

    ma_bo_phan = fields.Char(string='Mã bộ phận quản lý', readonly=True, copy=False)
    ten_bo_phan = fields.Char(string='Tên bộ phận quản lý', required=True)
    so_dien_thoai = fields.Char(string='Số điện thoại')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'ma_bo_phan' in fields_list:
            res['ma_bo_phan'] = self.env['ir.sequence'].next_by_code('bo.phan.quan.ly') or '/'
        return res 