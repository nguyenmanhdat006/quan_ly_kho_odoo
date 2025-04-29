from odoo import models, fields


class CertificateType(models.Model):
    _name = "certificate.type"
    _description = "Certificate Type"

    name = fields.Char(string="Name", required=True)
    issuing_organization_ids = fields.Many2many(
        "issuing.organization", string="Issuing Organizations"
    )
    description = fields.Text(string="Description")
