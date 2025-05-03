from odoo import models, fields, api
from datetime import date
from odoo.exceptions import ValidationError
import random
import string


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
    certificate_code = fields.Char(string="Certificate Code", readonly=True)
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
    uploaded_image = fields.Binary(string="Uploaded Image")

# random mã chứng chỉ
    @api.model
    def create(self, vals):
        if not vals.get('certificate_code'):
            vals['certificate_code'] = ''.join(random.choices(string.digits, k=10))
        return super(Certificate, self).create(vals)
    
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

    def action_revoke_certificate(self):
            """Set the status of the certificate to 'revoked'."""
            for record in self:
                record.status = 'revoked'