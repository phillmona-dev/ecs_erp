# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EcsFinanceTransactionType(models.Model):
    """
    Finance transaction type — drives per-company document sequencing.

    Each company configures its own set of transaction types (CPV, BPV,
    CRV, BRV, JV, etc.) linked to specific journals and sequences.
    The sequence generates reference numbers in the format:
        {CODE}/{ETHIOPIAN_YEAR}/{SEQUENCE_NO}
    e.g.  CPV/2016/00023

    Designed for company-isolated ECS finance operations.
    """
    _name = 'ecs.finance.transaction.type'
    _description = 'Finance Transaction Type'
    _order = 'company_id, code'

    name = fields.Char('Description', required=True)
    code = fields.Char(
        'Code', required=True, size=10,
        help='Short code used in reference numbers. e.g. CPV, BPV, CRV, JV'
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, default=lambda self: self.env.company,
        ondelete='restrict',
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Default Journal',
        domain="[('company_id','=',company_id)]",
    )
    transaction_category = fields.Selection([
        ('payment',  'Payment (Cash/Bank Out)'),
        ('receipt',  'Receipt (Cash/Bank In)'),
        ('journal',  'Journal Voucher'),
        ('import',   'Import / LC'),
        ('payroll',  'Payroll'),
        ('other',    'Other'),
    ], string='Category', default='journal')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'unique_code_per_company',
            'UNIQUE(code, company_id)',
            'Transaction type code must be unique per company.'
        )
    ]

    def get_next_reference(self, date=None):
        """
        Generate the next sequential reference number for this transaction type.
        Delegates to ecs.sequence.service for Ethiopian fiscal year formatting.
        """
        self.ensure_one()
        return self.env['ecs.sequence.service'].get_transaction_no(
            prefix=self.code,
            date=date,
            company_id=self.company_id.id,
        )
