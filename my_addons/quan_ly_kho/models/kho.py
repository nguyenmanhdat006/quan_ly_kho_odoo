from odoo import models, fields, api

class Kho(models.Model):
    _name = 'kho'
    _description = 'Kho'

    ma_kho = fields.Char(string='Mã kho', readonly=True, copy=False)
    ma_san_pham = fields.Many2one('san.pham', string='Mã sản phẩm', required=True)
    ten_san_pham = fields.Char(related='ma_san_pham.ten_san_pham', string='Tên sản phẩm', store=True)
    dia_chi = fields.Text(string='Địa chỉ')
    so_dien_thoai = fields.Char(string='Số điện thoại')
    so_luong_ton_kho = fields.Integer(string='Số lượng tồn kho', related='ma_san_pham.so_luong', store=True, readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'ma_kho' in fields_list:
            res['ma_kho'] = self.env['ir.sequence'].next_by_code('kho') or '/'
        return res