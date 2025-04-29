from odoo import models, fields


class IssuingOrganization(models.Model):
    _name = "issuing.organization"
    _description = "Issuing Organization"

    name = fields.Char("Organization Name", required=True)
    certification_type_ids = fields.Many2many("certificate.type", string="Certification Types")

    contact_info = fields.Text("Contact Information")
