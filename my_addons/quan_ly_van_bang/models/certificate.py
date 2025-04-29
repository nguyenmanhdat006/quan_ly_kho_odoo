from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError


class Certificate(models.Model):
    _name = "quanly.certificate"
    _description = "Certificate"

    student_id = fields.Many2one("quanly.student", string="Student", required=True)
    certificate_type_id = fields.Many2one(
        "certificate.type", string="Certificate Type", required=True
    )
    issuing_organization_id = fields.Many2one(
        "issuing.organization", string="Issuing Organization", required=True
    )
    certificate_code = fields.Char(string="Certificate Code")
    issue_date = fields.Date(string="Issue Date")
    expiration_date = fields.Date(string="Expiration Date")
    status = fields.Selection(
        [
            ("valid", "Valid"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        string="Status",
        default="valid",
    )
    file_url = fields.Char(string="File URL")

    @api.constrains("issue_date", "expiration_date")
    def _check_dates_and_expire(self):
        today = date.today()
        for record in self:
            # Nếu ngày cấp lớn hơn ngày hết hạn => lỗi logic => status = 'expired'
            if record.issue_date and record.expiration_date:
                if record.issue_date > record.expiration_date:
                    raise ValidationError("Ngày cấp không thể lớn hơn ngày hết hạn.")
            # Nếu ngày hết hạn nhỏ hơn hôm nay => đã hết hạn => status = 'expired'
            if record.expiration_date and record.expiration_date < today:
                record.status = 'expired'
