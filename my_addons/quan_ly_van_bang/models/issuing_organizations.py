from odoo import models, fields


class IssuingOrganization(models.Model):
    _name = "issuing.organization"
    _description = "Issuing Organization"

    name = fields.Char("Organization Name", required=True)
    contact_info = fields.Text("Contact Information")
