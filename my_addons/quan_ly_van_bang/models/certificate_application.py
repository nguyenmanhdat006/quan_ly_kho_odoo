from odoo import models, fields
from datetime import date


class CertificateApplication(models.Model):
    _name = "certificate.application"
    _description = "Đơn Đăng Ký Cấp Chứng Chỉ"

    name = fields.Char(string="Mã Đơn", required=True, readonly=True, default="Mới")
    student_id = fields.Many2one("quanly.student", string="Học Viên", required=True)
    certificate_type_id = fields.Many2one(
        "certificate.type", string="Loại Chứng Chỉ", required=True
    )
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
    )
    notes = fields.Text(string="Ghi Chú")
    issuing_organization_id = fields.Many2one(
        "issuing.organization", string="Tổ Chức Cấp Chứng Chỉ"
    )

    def action_accept(self):
        for record in self:
            record.status = "approved"
            record.env["quanly.certificate"].create(
                {
                    "student_id": record.student_id.id,
                    "certificate_type_id": record.certificate_type_id.id,
                    "issue_date": date.today(),
                    "status": "valid",
                    "issuing_organization_id": record.issuing_organization_id.id,
                }
            )

            record.env["certificate.status.logs"].create(
                {
                    "certificate_application_id": record.id,
                    "old_status": record.status,
                    "new_status": record.status,
                    "changed_by": self.env.user.id,
                    "change_date": fields.Datetime.now(),
                    "notes": "Đơn đã được duyệt và chứng chỉ đã tạo.",
                }
            )

    def action_refuse(self):
        for record in self:
            record.status = "rejected"

            record.env["certificate.status.logs"].create(
                {
                    "certificate_application_id": record.id,
                    "old_status": record.status,
                    "new_status": record.status,
                    "changed_by": self.env.user.id,
                    "change_date": fields.Datetime.now(),
                    "notes": "Đơn bị từ chối.",
                }
            )
