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
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    extension_days = fields.Integer(
        string="Extension Days",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    new_due_date = fields.Date(
        string="New Due Date",
        compute="_compute_new_due_date",
        store=True,
        readonly=True,
    )

    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")],
        default="draft",
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

    @api.constrains("extension_days")
    def _check_extension_days(self):
        for rec in self:
            if rec.extension_days <= 0:
                raise exceptions.ValidationError("Extension days must be greater than zero.")

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._apply_extension_sql()
        return rec

    def write(self, vals):
        if any(r.state == "done" for r in self):
            raise exceptions.UserError("You cannot modify a record that is already processed.")
        res = super().write(vals)
        self._apply_extension_sql()
        self.state = "done"
        return res

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
                    rec.state = "done"
