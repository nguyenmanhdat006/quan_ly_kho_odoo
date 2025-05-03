from odoo import models, fields

class CertificateStatusLogs(models.Model):
    _name = "certificate.status.logs"
    _description = "Logs for Certificate Status Changes"

    certificate_application_id = fields.Many2one(
        "certificate.application", string="Mã đơn", required=True
    )
    old_status = fields.Selection(
        [
            ("pending", "Đang Chờ Duyệt"),
            ("approved", "Đã Duyệt"),
            ("rejected", "Bị Từ Chối"),
        ],
        string="Old Status",
        required=True,
    )
    new_status = fields.Selection(
        [
            ("pending", "Đang Chờ Duyệt"),
            ("approved", "Đã Duyệt"),
            ("rejected", "Bị Từ Chối"),
        ],
        string="New Status",
        required=True,
    )
    changed_by = fields.Many2one("res.users", string="Changed By", required=True)
    change_date = fields.Datetime(string="Change Date", required=True)
    notes = fields.Text(string="Notes")