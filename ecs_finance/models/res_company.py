# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """
    Company-level configuration flags for ECS ERP.

    Finance administrators can toggle these settings per company.
    """
    _inherit = 'res.company'

    # ── Procurement settings ──────────────────────────────────────────
    bypass_budget_check = fields.Boolean(
        'Bypass Budget Check on Purchase Requests',
        default=False,
        help='If enabled, purchase requests do not require a budget position. '
             'Use only for companies whose procurement policy allows it.',
    )

    # ── Finance settings ──────────────────────────────────────────────
    require_payment_request = fields.Boolean(
        'Require Payment Request Before Payment',
        default=True,
        help='If enabled, all outbound payments must be linked to an approved '
             'payment request.',
    )
    default_withholding_journal_id = fields.Many2one(
        'account.journal',
        string='Default Withholding Journal',
        domain="[('company_id','=',id),('type','=','general')]",
        help='Default journal for withholding tax entries.',
    )

    # ── Ethiopian fiscal year ─────────────────────────────────────────
    et_fiscal_year_start_month = fields.Integer(
        'ET Fiscal Year Start Month (Gregorian)',
        default=7,
        help='Month of Gregorian calendar when Ethiopian fiscal year starts. '
             'Default: 7 (July — corresponds to Hamile).',
    )
    et_fiscal_year_start_day = fields.Integer(
        'ET Fiscal Year Start Day',
        default=8,
        help='Day of the start month. Default: 8 (Hamile 1 = July 8 Gregorian).',
    )
