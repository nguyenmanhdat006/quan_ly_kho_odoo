from odoo import models, fields

class CertificateApplication(models.Model):
    _name = 'certificate.application'
    _description = 'Đơn Đăng Ký Cấp Chứng Chỉ'

    name = fields.Char(string='Mã Đơn', required=True, readonly=True, default='Mới')
    student_id = fields.Many2one('res.partner', string='Học Viên', required=True)
    certificate_type_id = fields.Many2one('certificate.type', string='Loại Chứng Chỉ', required=True)
    apply_date = fields.Datetime(string='Ngày Đăng Ký', default=fields.Datetime.now)
    status = fields.Selection([
        ('pending', 'Đang Chờ Duyệt'),
        ('approved', 'Đã Duyệt'),
        ('rejected', 'Bị Từ Chối')
    ], string='Trạng Thái', default='pending', required=True)
    notes = fields.Text(string='Ghi Chú')
