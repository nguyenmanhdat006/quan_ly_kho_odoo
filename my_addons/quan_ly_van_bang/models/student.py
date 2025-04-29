from odoo import models, fields

class Certificate(models.Model):
    _name = 'quanly.certificate'
    _description = 'Certificate'

    name = fields.Char(string='Certificate Name', required=True)
    issue_date = fields.Date(string='Issue Date')
    expiration_date = fields.Date(string='Expiration Date')
    issuing_authority = fields.Char(string='Issuing Authority')

    student_id = fields.Many2one('quanly.student', string='Student', ondelete='cascade')
