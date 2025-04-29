from odoo import models, fields

class Student(models.Model):
    _name = 'quanly.student'
    _description = 'Student'

    full_name = fields.Char(string="Full Name", required=True)
    date_of_birth = fields.Date(string="Date of Birth")
    national_id = fields.Char(string="National ID")
    email = fields.Char(string="Email")
    phone_number = fields.Char(string="Phone Number")
    address = fields.Text(string="Address")

    certificate_ids = fields.One2many(
        'quanly.certificate', 'student_id', string="Certificates"
    )


