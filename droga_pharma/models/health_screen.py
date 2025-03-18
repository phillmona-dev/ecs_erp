from odoo import fields, models, api
from odoo.exceptions import UserError
import logging
import pdfkit
import base64

_logger = logging.getLogger(__name__)

class DrogaHealthScreening(models.Model):
    _name = 'droga.health.screening'
    _description = "Droga Pharma Form"

    client_id = fields.Many2one('res.partner.pharma2',string='name')
    age = fields.Integer(string="Age")
    mobile = fields.Char(string="Mobile Number", compute="_compute_mobile", store=True)
    sex = fields.Selection([('female', 'Female'), ('male', 'Male')], string="Sex")
    patient_condition = fields.Char(string="Patient Condition")
    weight = fields.Float(string="Weight (KG)")
    bp_systolic = fields.Integer(string="Systolic BP (mmHg)")
    bp_diastolic = fields.Integer(string="Diastolic BP (mmHg)")
    fasting_glucose = fields.Float(string="Fasting Blood Glucose (mg/dL)")
    rbs_glucose = fields.Float(string="Postprandial Blood Glucose (mg/dL)")
    sale_order_id = fields.Many2one('sale.order', string="Sales Order")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    pdf_report = fields.Binary("Generated PDF", readonly=True)
    pdf_filename = fields.Char("PDF Filename")

    screening_type = fields.Selection([
        ('glucose', 'Glucose Test'),
        ('bp', 'Blood Pressure Test'),
        ('weight', 'Weight Measurement')
    ], string="Screening Type", required=True)

    @api.depends('client_id.partner.mobile', 'client_id.partner.phone')
    def _compute_mobile(self):
        for rec in self:
            if rec.client_id and rec.client_id.partner:
                mobile = rec.client_id.partner.mobile or rec.client_id.partner.phone or ''
                rec.mobile = mobile.replace(" ", "").replace("251", "0")  # Format phone number
            else:
                rec.mobile = ''


    @api.onchange('fasting_glucose', 'rbs_glucose')
    def _onchange_glucose_fields(self):
        if self.fasting_glucose:
            self.rbs_glucose = False
        if self.rbs_glucose:
            self.fasting_glucose = False


    def action_create_payment(self):

        self.ensure_one()
        sale_order = self.sale_order_id

        if sale_order and sale_order.state != 'draft':
            sale_order = sale_order.copy({'state': 'draft'})
            self.write({'sale_order_id': sale_order.id})


        if sale_order:
            return {
                'name': 'Sales Order',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order',
                'view_id': self.env.ref('droga_pharma.view_order_form_pharma').id,
                'type': 'ir.actions.act_window',
                'res_id': sale_order.id,
            }

        if not self.client_id or not self.client_id.partner:
            raise UserError("Please select a valid customer before creating the sales order.")

        customer = self.client_id.partner

        default_product = self.env['product.product'].search([('sale_ok', '=', True)], limit=1)
        if not default_product:
            raise UserError("No products available in the catalog. Please add at least one saleable product.")

        sale_order_vals = {
            'partner_id': customer.id,
            'partner_custom': self.client_id.id,
            'client_order_ref': self.client_id.name,
            'order_line': [(0, 0, {
                'product_id': default_product.id,
                'name': default_product.name,
                'product_uom': default_product.uom_id.id,
                'product_uom_qty': 1,
                'price_unit': 120.0,
            })],
            'state': 'draft',
            'payment_term_id': 11,
            'date_order': fields.Datetime.now(),
            'order_from': 'PH',
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        self.write({'sale_order_id': sale_order.id})


        return {
            'name': 'Sales Order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': self.env.ref('droga_pharma.view_order_form_pharma').id,
            'type': 'ir.actions.act_window',
            'res_id': sale_order.id,
        }

    def generate_pdf_report(self):
        self.ensure_one()
        company = self.env.company
        if company.logo_web:
            logo_data = base64.b64decode(company.logo_web)
            logo_base64 = base64.b64encode(logo_data).decode('utf-8')
            img_url = f"data:image/png;base64,{logo_base64}"
        else:
            img_url = ""
        html_content = f"""
        <html>
        <head>
            <title>Health Screening Report</title>
            <style>
                body {{font-family: Arial, sans-serif;margin: 20px;text-align: left;  }}
                .header, .footer {{width: 100%;text-align: center;font-size: 12px;}}
                .header-table {{width: 100%;border-bottom: 2px solid black;margin-bottom: 10px;}}
                .header-table td, .footer-table td {{padding: 5px;}}
                .header-left, .footer-left {{text-align: left;}}
                .header-right, .footer-right {{text-align: right;}}
                .report-title {{text-align: center;font-size: 18px;font-weight: bold;color: #4CAF50;margin-bottom: 20px;padding-top: 20px;}}
                .content-table {{width: 100%;border-collapse: collapse;margin-top: 10px;}}
                .content-table th, .content-table td {{border: 1px solid #ddd;padding: 8px;text-align: left; }}
                .content-table th {{background-color: #f2f2f2;}}
                .footer {{position: fixed;bottom: 0;width: 100%;text-align: center;font-size: 12px;padding: 10px 0;margin-top: auto;background-color: white;}}
                .footer-table {{width: 100%;margin-top: 10px;}}
                .header-img {{max-width: 310px;height: 90px;width: 140px; display: block;margin-left: auto; margin-right: auto;}}
            </style>
        </head>
        <body>

            <!-- Header -->
            <table class="header-table">
                <tr>
                    <td class="header-left">
                        <strong>DROGA PHARMACY</strong><br>
                        ፍርግ ፋርማሲ<br>
                        +251965757515, +251966565664
                    </td>
                    <td class="header-center">
                        <img src="{img_url}" class="header-img" alt="Droga Pharmacy Logo">
                    </td>
                    <td class="header-right">
                        <strong>Looking After Your Health!</strong><br>
                        እህልን ይጠብቁ!
                    </td>
                </tr>
            </table>

            <!-- Report Title -->
            <div class="report-title">Health Screening Report</div>

            <!-- Report Content -->
            <p><strong>Patient:</strong> {self.client_id.name}</p>
            <p><strong>Age:</strong> {self.age}</p>
            <p><strong>Sex:</strong> {self.sex}</p>
            <p><strong>Weight:</strong> {self.weight} KG</p>
            <p><strong>Systolic BP:</strong> {self.bp_systolic} mmHg</p>
            <p><strong>Diastolic BP:</strong> {self.bp_diastolic} mmHg</p>
            <p><strong>Fasting Glucose:</strong> {self.fasting_glucose} mg/dL</p>
            <p><strong>RBS Glucose:</strong> {self.rbs_glucose} mg/dL</p>

            <!-- Footer -->
            <div class="footer">
                <table class="footer-table">
                    <tr>
                        <td class="footer-left">
                            Region: Addis Ababa &nbsp; | &nbsp; Subcity: Arada &nbsp; | &nbsp; Woreda: 08 &nbsp; | &nbsp; Kebelle: 14 &nbsp; | &nbsp; House No.: 379
                        </td>
                    </tr>
                    <tr>
                        <td class="footer-left">
                            Email: info@drogapharmacy.com &nbsp; | &nbsp; Web: <a href="https://drogapharmacy.com">https://drogapharmacy.com</a> &nbsp; | &nbsp; Tin: 0045080232
                        </td>
                    </tr>
                </table>
            </div>

        </body>
        </html>
        """

        options = {
            'quiet': '',
            'page-size': 'A4',
            'encoding': 'UTF-8',
            'enable-local-file-access': '',
        }

        pdf_data = pdfkit.from_string(html_content, False, options=options)

        pdf_filename = f"Health_Screening_{self.id}.pdf"
        self.write({
            'pdf_report': base64.b64encode(pdf_data),
            'pdf_filename': pdf_filename
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{self._name}/{self.id}/pdf_report/{pdf_filename}?download=true",
            'target': 'self',
        }
