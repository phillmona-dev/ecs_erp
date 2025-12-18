# models/invoice_extension.py
from odoo import models, fields, api, exceptions
from datetime import timedelta

class InvoiceExtension(models.Model):
    _name = "invoice.extension"
    _description = "Invoice Due Date Extension"
    _rec_name = "invoice_id"

    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
    )

    extension_days = fields.Integer(
        string="Extension Days",
        required=True,
    )

    new_due_date = fields.Date(
        string="New Due Date",
        compute="_compute_new_due_date",
        store=True,
        readonly=True,
    )

    @api.depends("invoice_id", "extension_days")
    def _compute_new_due_date(self):
        for rec in self:
            if rec.invoice_id and rec.invoice_id.invoice_date_due:
                original_due = rec.invoice_id.invoice_date_due
                rec.new_due_date = original_due + timedelta(days=rec.extension_days)
            else:
                rec.new_due_date = False

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._apply_extension_sql()
        return rec

    def _apply_extension_sql(self):
        """Update invoice due date using direct SQL for performance and control."""
        for rec in self:
            if rec.invoice_id:
                if rec.new_due_date:
                    query = """
                        UPDATE account_move
                        SET invoice_date_due = %s
                        WHERE id = %s;
                    """
                    self.env.cr.execute(query, (rec.new_due_date, rec.invoice_id.id))

