from odoo import models, fields,api

class CertificateArchive(models.Model):
    _name = "certificate.archive"
    _description = "Certificate Archive"

    certificate_id = fields.Many2one("quanly.certificate", string="Certificate", required=True)
    student_id = fields.Many2one("quanly.student", string="Student", related="certificate_id.student_id", store=True)
    certificate_type_id = fields.Many2one("certificate.type", string="Certificate Type", related="certificate_id.certificate_type_id", store=True)
    issuing_organization_id = fields.Many2one("issuing.organization", string="Issuing Organization", related="certificate_id.issuing_organization_id", store=True)
    certificate_code = fields.Char(string="Certificate Code", related="certificate_id.certificate_code", store=True)
    issue_date = fields.Date(string="Issue Date", related="certificate_id.issue_date", store=True)
    expiration_date = fields.Date(string="Expiration Date", related="certificate_id.expiration_date", store=True)
    status = fields.Selection(
        [
            ("valid", "Valid"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        string="Status",
        related="certificate_id.status",
        store=True,
    )
    file_url = fields.Char(string="File URL", readonly=True)  # Thêm trường này
    uploaded_image = fields.Binary(string="Uploaded Image", readonly=True)

    @api.model
    def action_restore(self):
        pass