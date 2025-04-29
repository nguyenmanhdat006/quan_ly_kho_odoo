from odoo import models, fields

class Certificate(models.Model):
    _name = 'quanly.certificate'
    _description = 'Certificate'

    student_id = fields.Many2one('quanly.student', string='Student', required=True)
    certificate_type_id = fields.Many2one('certificate.type', string='Certificate Type', required=True)
    issuing_organization_id = fields.Many2one('issuing.organization', string='Issuing Organization', required=True)
    certificate_code = fields.Char(string='Certificate Code')
    issue_date = fields.Date(string='Issue Date')
    expiration_date = fields.Date(string='Expiration Date')
    status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ], string='Status', default='valid')
    file_url = fields.Char(string='File URL')


