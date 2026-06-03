# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class EcsSequenceService(models.Model):
    """
    Per-company, per-prefix sequential transaction number generator.

    Company-scoped, upgrade-safe implementation that uses ir.sequence under
    the hood.

    Format:  {PREFIX}/{ETHIOPIAN_FISCAL_YEAR}/{SEQ:05d}
    Example: CPV/2016/00123   (CPV = Cash Payment Voucher, 2016 = Ethiopian year)

    Usage:
        ref = self.env['ecs.sequence.service'].get_transaction_no(
            prefix='PR',
            date=fields.Date.today(),
            company_id=self.env.company.id,
        )
    """
    _name = 'ecs.sequence.service'
    _description = 'ECS Transaction Number Generator'

    # Ethiopian calendar offset: Gregorian year − 7 or − 8 (after Sept 11)
    _ET_MONTH_OFFSET = 8   # months before September 11 subtract 8; after subtract 7

    @api.model
    def get_transaction_no(self, prefix, date=None, company_id=None):
        """
        Generate the next transaction number for a given prefix and company.

        :param prefix: str  — e.g. 'CPV', 'PR', 'PMR', 'EMP'
        :param date:   date — used to determine Ethiopian fiscal year
        :param company_id: int — res.company id; defaults to current company
        :return: str — formatted transaction reference
        """
        if date is None:
            date = fields.Date.today()
        if company_id is None:
            company_id = self.env.company.id

        et_year = self._gregorian_to_ethiopian_year(date)
        seq_code = f'ecs.seq.{prefix.lower()}.{company_id}'

        sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', seq_code),
            ('company_id', '=', company_id),
        ], limit=1)

        if not sequence:
            sequence = self._create_sequence(seq_code, prefix, company_id)

        next_number = sequence.next_by_id()
        return f'{prefix.upper()}/{et_year}/{next_number}'

    @api.model
    def _create_sequence(self, code, prefix, company_id):
        """Auto-create the ir.sequence if it doesn't exist yet."""
        company = self.env['res.company'].browse(company_id)
        _logger.info(
            'ECS Sequence Service: creating sequence %s for company %s',
            code, company.name
        )
        return self.env['ir.sequence'].sudo().create({
            'name': f'ECS {prefix.upper()} — {company.name}',
            'code': code,
            'company_id': company_id,
            'prefix': '',
            'padding': 5,
            'number_increment': 1,
            'number_next': 1,
            'implementation': 'no_gap',
        })

    @api.model
    def _gregorian_to_ethiopian_year(self, date):
        """
        Approximate Ethiopian calendar year from a Gregorian date.

        Ethiopian New Year falls around September 11 (Gregorian).
        Before Sept 11: ET year = Gregorian year - 8
        From Sept 11:   ET year = Gregorian year - 7
        """
        if hasattr(date, 'month'):
            month = date.month
            day = date.day
            year = date.year
        else:
            # Handle string dates
            from datetime import datetime
            d = datetime.strptime(str(date), '%Y-%m-%d')
            month, day, year = d.month, d.day, d.year

        if month > 9 or (month == 9 and day >= 11):
            return year - 7
        return year - 8
