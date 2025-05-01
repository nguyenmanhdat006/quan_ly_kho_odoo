from odoo import models, fields

class CertificateStatusLogs(models.Model):
    _name = 'certificate.status.logs'  
    _description = 'Certificate Status Logs' 

    certificate_application_id = fields.Many2one(
        'certificate.application', 
        string="Certificate Application", 
        required=True
    )
    old_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Old Status', required=True)
    
    new_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='New Status', required=True)
    
    changed_by = fields.Many2one(
        'res.users', 
        string='Changed By', 
        required=True
    )
    
    change_date = fields.Datetime(
        string='Change Date', 
        default=fields.Datetime.now
    )
    notes = fields.Text(string='Notes')
