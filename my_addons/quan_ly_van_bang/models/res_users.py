from odoo import models, fields

class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    student_ids = fields.One2many(
        'quanly.student', 'user_id', string="Students"
    )