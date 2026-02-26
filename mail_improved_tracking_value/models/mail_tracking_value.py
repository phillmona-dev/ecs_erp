# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from odoo import api, fields, models


class MailTrackingValue(models.Model):

    _inherit = "mail.tracking.value"

    new_value_formatted = fields.Char(
        compute="_compute_formatted_value", string="New value"
    )
    old_value_formatted = fields.Char(
        compute="_compute_formatted_value", string="Old value"
    )
    record_name = fields.Char(related="mail_message_id.record_name", readonly=True)
    model = fields.Char(related="mail_message_id.model", store=True, readonly=True, string="Model")
    field_desc = fields.Char(compute="_compute_field_desc", string="Field changed")

    @api.depends("field_id", "field_info")
    def _compute_field_desc(self):
        for record in self:
            record.field_desc = (
                record.field_id.field_description
                or (record.field_info or {}).get("desc")
                or ""
            )

    @api.depends(
        "field_id",
        "field_info",
        "currency_id",
        "new_value_char",
        "new_value_integer",
        "new_value_float",
        "new_value_text",
        "new_value_datetime",
        "old_value_char",
        "old_value_integer",
        "old_value_float",
        "old_value_text",
        "old_value_datetime",
    )
    def _compute_formatted_value(self):
        """Sets the value formatted field used in the view"""
        for record in self:
            field_type = record.field_id.ttype or (record.field_info or {}).get("type")

            if field_type in ("many2many", "one2many", "char", "selection", "many2one", "tags"):
                record.new_value_formatted = record.new_value_char
                record.old_value_formatted = record.old_value_char
            elif field_type in ("integer", "boolean"):
                record.new_value_formatted = (
                    str(record.new_value_integer) if record.new_value_integer is not False else ""
                )
                record.old_value_formatted = (
                    str(record.old_value_integer) if record.old_value_integer is not False else ""
                )
            elif field_type in ("float", "monetary"):
                record.new_value_formatted = (
                    str(record.new_value_float) if record.new_value_float is not False else ""
                )
                record.old_value_formatted = (
                    str(record.old_value_float) if record.old_value_float is not False else ""
                )
            elif field_type in ("datetime", "date"):
                record.new_value_formatted = (
                    str(record.new_value_datetime) if record.new_value_datetime else ""
                )
                record.old_value_formatted = (
                    str(record.old_value_datetime) if record.old_value_datetime else ""
                )
            elif field_type == "text":
                record.new_value_formatted = record.new_value_text
                record.old_value_formatted = record.old_value_text
            else:
                record.new_value_formatted = (
                    record.new_value_char
                    or record.new_value_text
                    or (str(record.new_value_float) if record.new_value_float is not False else "")
                )
                record.old_value_formatted = (
                    record.old_value_char
                    or record.old_value_text
                    or (str(record.old_value_float) if record.old_value_float is not False else "")
                )

    @api.model
    def _create_tracking_values(
        self,
        initial_value,
        new_value,
        col_name,
        col_info,
        record,
    ):
        """Add tracking capabilities for many2many and one2many fields."""
        if col_info["type"] in ("many2many", "one2many"):
            def get_values(source, prefix):
                if source:
                    if isinstance(source, models.BaseModel):
                        names = ", ".join(source.exists().mapped("display_name"))
                        json_ids = json.dumps(source.ids)
                    else:
                        names = ", ".join(v[1] for v in source if isinstance(v, (list, tuple)) and len(v) > 1)
                        json_ids = json.dumps([v[0] for v in source if isinstance(v, (list, tuple)) and v])
                else:
                    names = ""
                    json_ids = json.dumps([])
                return {
                    "{}_value_char".format(prefix): names,
                    "{}_value_text".format(prefix): json_ids,
                }

            field = self.env["ir.model.fields"]._get(record._name, col_name)
            if not field:
                raise ValueError(f"Unknown field {col_name} on model {record._name}")

            values = {"field_id": field.id}
            values.update(get_values(initial_value, "old"))
            values.update(get_values(new_value, "new"))
            return values
        return super()._create_tracking_values(
            initial_value,
            new_value,
            col_name,
            col_info,
            record,
        )
