# -*- coding: utf-8 -*-
from odoo import models, api


class EcsCurrencyWordMixin(models.AbstractModel):
    """
    Mixin: converts a float monetary amount to Ethiopian Birr words.

    All ECS modules needing amount-in-words should inherit this mixin.

    Usage:
        class MyModel(models.Model):
            _inherit = ['my.model', 'ecs.currency.word.mixin']

            amount_in_words = fields.Char(compute='_compute_amount_in_words')

            def _compute_amount_in_words(self):
                for rec in self:
                    rec.amount_in_words = self.amount_to_word(rec.amount_total)
    """
    _name = 'ecs.currency.word.mixin'
    _description = 'ECS Amount in Words (ETB) Mixin'

    # ── Ones and teens ────────────────────────────────────────────────
    _ONES = [
        '', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
        'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
        'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen',
    ]
    _TENS = [
        '', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
        'Sixty', 'Seventy', 'Eighty', 'Ninety',
    ]

    @api.model
    def amount_to_word(self, amount, currency_name='ETB'):
        """
        Convert a float amount to Ethiopian Birr words.

        :param amount: float — the monetary amount
        :param currency_name: str — currency label (default ETB)
        :return: str — e.g. "One Thousand Five Hundred Birr and Fifty Cents"
        """
        if amount is None or amount < 0:
            return ''
        birr = int(amount)
        cents = round((amount - birr) * 100)
        birr_word = self._int_to_word(birr).strip()
        if cents > 0:
            cent_word = self._int_to_word(cents).strip()
            return f'{birr_word} Birr and {cent_word} Cents'
        return f'{birr_word} Birr Only'

    @api.model
    def _int_to_word(self, n):
        """Recursively convert an integer to English words."""
        if n == 0:
            return 'Zero'
        if n < 0:
            return 'Negative ' + self._int_to_word(-n)
        if n < 20:
            return self._ONES[n]
        if n < 100:
            tens = self._TENS[n // 10]
            ones = self._ONES[n % 10]
            return tens + (' ' + ones if ones else '')
        if n < 1_000:
            hundreds = self._ONES[n // 100] + ' Hundred'
            remainder = n % 100
            return hundreds + (' ' + self._int_to_word(remainder) if remainder else '')
        if n < 1_000_000:
            thousands = self._int_to_word(n // 1_000) + ' Thousand'
            remainder = n % 1_000
            return thousands + (' ' + self._int_to_word(remainder) if remainder else '')
        if n < 1_000_000_000:
            millions = self._int_to_word(n // 1_000_000) + ' Million'
            remainder = n % 1_000_000
            return millions + (' ' + self._int_to_word(remainder) if remainder else '')
        billions = self._int_to_word(n // 1_000_000_000) + ' Billion'
        remainder = n % 1_000_000_000
        return billions + (' ' + self._int_to_word(remainder) if remainder else '')
