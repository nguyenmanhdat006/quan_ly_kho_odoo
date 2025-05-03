from odoo import models, fields, api
from datetime import date


class CertificateApplication(models.Model):
    _name = "certificate.application"
    _description = "Đơn Đăng Ký Cấp Chứng Chỉ"

    name = fields.Char(
    string="Mã Đơn",
    required=True,
    readonly=True,
    copy=False,
    default='/'
)


    student_id = fields.Many2one("quanly.student", string="Học Viên", required=True)
    certificate_type_id = fields.Many2one("certificate.type", string="Loại Chứng Chỉ", required=True)
    issuing_organization_id = fields.Many2one("issuing.organization", string="Tổ Chức Cấp Chứng Chỉ" , required=True)
    file_url = fields.Char(string="File URL")
    uploaded_image = fields.Binary(string="Uploaded Image")
    apply_date = fields.Datetime(string="Ngày Đăng Ký", default=fields.Datetime.now)
    
    status = fields.Selection(
        [
            ("pending", "Đang Chờ Duyệt"),
            ("approved", "Đã Duyệt"),
            ("rejected", "Bị Từ Chối"),
        ],
        string="Trạng Thái",
        default="pending",
        required=True,
        readonly=True,
        tracking=True,
    )
    notes = fields.Text(string="Ghi Chú")
    issuing_organization_id = fields.Many2one(
        "issuing.organization", string="Tổ Chức Cấp Chứng Chỉ"
    )

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('certificate.application') or '/'
        return super(CertificateApplication, self).create(vals)


    def action_accept(self):
        for record in self:
            if record.status != "pending":
                continue
            record.status = "approved"

            # Tạo bản ghi chứng chỉ
            self.env["quanly.certificate"].create({
                "student_id": record.student_id.id,
                "certificate_type_id": record.certificate_type_id.id,
                "issuing_organization_id": record.issuing_organization_id.id,
                "file_url": record.file_url,
                "uploaded_image": record.uploaded_image,
                "issue_date": date.today(),
                "status": "valid",
            })

            # Ghi log trạng thái
            self.env["certificate.status.logs"].create({
                "certificate_application_id": record.id,
                "old_status": "pending",
                "new_status": "approved",
                "changed_by": self.env.user.id,
                "change_date": fields.Datetime.now(),
                "notes": "Đơn đã được duyệt và chứng chỉ đã tạo.",
            })

    def action_refuse(self):
        for record in self:
            if record.status != "pending":
                continue
            record.status = "rejected"

            self.env["certificate.status.logs"].create({
                "certificate_application_id": record.id,
                "old_status": "pending",
                "new_status": "rejected",
                "changed_by": self.env.user.id,
                "change_date": fields.Datetime.now(),
                "notes": "Đơn bị từ chối.",
            })
    @api.model
    def _is_admin(self):
        return self.env.user.has_group('quan_ly_van_bang.group_qlvb_admin')  

    def _compute_readonly(self):
        for record in self:
            record.readonly_status = (
                record.status in ['approved', 'rejected'] and not self._is_admin()
            )
    readonly_status = fields.Boolean(compute="_compute_readonly", store=False)
    
