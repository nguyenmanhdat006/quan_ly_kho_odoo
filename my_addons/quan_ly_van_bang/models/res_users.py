from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class ResUsersInherit(models.Model):
    _inherit = "res.users"

    certificate_ids = fields.One2many(
        "quanly.certificate", "user_id", string="Certificates"
    )

    date_of_birth = fields.Date(string="Date of Birth")
    national_id = fields.Char(string="National ID")
    address = fields.Text(string="Address")

    certificate_ids = fields.One2many(
        "quanly.certificate", "student_id", string="Certificates"
    )

    @api.constrains("email")
    def _check_email(self):
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        for record in self:
            if record.email and not re.match(email_regex, record.email):
                raise ValidationError("Email không hợp lệ.")

    @api.constrains("phone_number")
    def _check_phone_number(self):
        phone_regex = r"^\+?\d{9,15}$"
        for record in self:
            if record.phone_number and not re.match(phone_regex, record.phone_number):
                raise ValidationError(
                    "Số điện thoại không hợp lệ. Phải có từ 9 đến 15 chữ số, có thể bắt đầu bằng +."
                )
