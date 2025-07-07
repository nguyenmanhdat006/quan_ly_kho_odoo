from odoo import models, fields, api

class PhieuNhap(models.Model):
    _name = 'phieu.nhap'
    _description = 'Phiếu nhập'

    ma_phieu = fields.Char(string='Mã phiếu', readonly=True, copy=False, default='New')
    ma_san_pham = fields.Many2one('san.pham', string='Mã sản phẩm', required=True)
    ma_nhan_vien = fields.Many2one('nhan.vien', string='Mã nhân viên', required=True)
    ten_san_pham = fields.Char(related='ma_san_pham.ten_san_pham', string='Tên sản phẩm', store=True)
    so_luong = fields.Integer(string='Số lượng')
    don_gia_mua = fields.Float(string='Đơn giá mua')
    gia_nhap = fields.Float(string='Giá nhập', compute='_compute_gia_nhap', store=True)
    ngay_nhap = fields.Date(string='Ngày nhập')

    @api.depends('so_luong', 'don_gia_mua')
    def _compute_gia_nhap(self):
        for record in self:
            record.gia_nhap = record.so_luong * record.don_gia_mua

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ma_phieu', 'New') == 'New':
                vals['ma_phieu'] = self.env['ir.sequence'].next_by_code('phieu.nhap') or 'New'
        records = super().create(vals_list)
        for record in records:
            if record.ma_san_pham and record.so_luong:
                record.ma_san_pham.so_luong += record.so_luong
        return records