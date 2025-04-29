from odoo import models, fields

class CertificateType(models.Model):
    _name = 'certificate.type'
    _description = 'Certificate Type'

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
