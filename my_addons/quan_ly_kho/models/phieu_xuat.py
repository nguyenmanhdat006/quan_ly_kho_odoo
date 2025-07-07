from odoo import models, fields, api
from odoo.exceptions import UserError

class PhieuXuat(models.Model):
    _name = 'phieu.xuat'
    _description = 'Phiếu xuất'

    ma_phieu = fields.Char(string='Mã phiếu', readonly=True, copy=False, default='New')
    ma_san_pham = fields.Many2one('san.pham', string='Mã sản phẩm', required=True)
    ma_nhan_vien = fields.Many2one('nhan.vien', string='Mã nhân viên', required=True)
    ten_san_pham = fields.Char(related='ma_san_pham.ten_san_pham', string='Tên sản phẩm', store=True)
    so_luong = fields.Integer(string='Số lượng')
    gia_ban = fields.Float(string='Giá bán')
    don_gia_ban = fields.Float(string='Đơn giá bán', compute='_compute_don_gia_ban', store=True)
    ngay_xuat = fields.Date(string='Ngày xuất')

    @api.depends('so_luong', 'gia_ban')
    def _compute_don_gia_ban(self):
        for record in self:
            record.don_gia_ban = record.so_luong * record.gia_ban

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ma_phieu', 'New') == 'New':
                vals['ma_phieu'] = self.env['ir.sequence'].next_by_code('phieu.xuat') or 'New'
        records = super().create(vals_list)
        for record in records:
            if record.ma_san_pham and record.so_luong:
                if record.ma_san_pham.so_luong < record.so_luong:
                    raise UserError("Số lượng tồn kho không đủ để xuất!")
                record.ma_san_pham.so_luong -= record.so_luong
        return records