# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EcsWithholdingConfig(models.Model):
    """
    Per-company withholding tax configuration.

    Finance managers configure this once per company via Settings, then all
    withholding entries are generated dynamically from this table.
    """
    _name = 'ecs.finance.withholding.config'
    _description = 'Withholding Tax Configuration'
    _order = 'company_id, partner_type'

    name = fields.Char(
        'Configuration Name', required=True,
        help='e.g. "Goods Supplier 2%" or "Service Provider 30%"'
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, default=lambda self: self.env.company,
        ondelete='restrict',
    )
    partner_type = fields.Selection([
        ('goods',    'Goods Supplier'),
        ('services', 'Service Provider'),
        ('rent',     'Rental Payment'),
        ('import',   'Import Duty / Customs'),
        ('employee', 'Employee (PAYE)'),
        ('other',    'Other'),
    ], string='Applicable To', required=True)

    rate = fields.Float(
        'Withholding Rate (%)', required=True, digits=(5, 2),
        help='Percentage withheld from the gross invoice amount.'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Withholding Payable Account',
        required=True,
        domain="[('deprecated','=',False)]",
        help='Liability account where withholding amounts are credited.'
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Withholding Journal',
        required=True,
        domain="[('company_id','=',company_id),('type','=','general')]",
        help='Journal used when posting the withholding journal entry.'
    )
    active = fields.Boolean(default=True)
    note   = fields.Text('Notes')

    _sql_constraints = [
        (
            'unique_partner_type_per_company',
            'UNIQUE(company_id, partner_type)',
            'Only one withholding configuration per partner type per company is allowed. '
            'Please update the existing configuration instead of creating a new one.'
        )
    ]

    @api.constrains('rate')
    def _check_rate(self):
        for rec in self:
            if not (0 < rec.rate <= 100):
                raise ValidationError(
                    _('Withholding rate must be between 0%% and 100%%. Got: %s%%') % rec.rate
                )

    def compute_withholding_amount(self, gross_amount):
        """Return the withholding amount for a given gross invoice amount."""
        self.ensure_one()
        return gross_amount * self.rate / 100.0

    @api.model
    def get_config_for_partner(self, partner, company_id=None):
        """
        Lookup the withholding config for a vendor partner.
        Determines partner_type from partner category or manual flag.

        :param partner: res.partner record
        :param company_id: int (defaults to current company)
        :return: EcsWithholdingConfig record or empty recordset
        """
        if company_id is None:
            company_id = self.env.company.id

        # Determine partner type — extend this logic as needed
        if partner.is_company and partner.supplier_rank > 0:
            p_type = 'services' if getattr(partner, 'x_is_service_provider', False) else 'goods'
        else:
            p_type = 'goods'

        return self.search([
            ('company_id', '=', company_id),
            ('partner_type', '=', p_type),
            ('active', '=', True),
        ], limit=1)
