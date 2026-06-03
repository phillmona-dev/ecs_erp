# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class EcsConsolidatedCashPosition(models.TransientModel):
    """
    Consolidated Cash & Bank position across multiple companies.
    Fetches balance from all bank & cash type journals.
    """
    _name = 'ecs.consolidated.cash.position'
    _description = 'Consolidated Cash Position'

    name = fields.Char(string='Report Title', default='Consolidated Cash Position')
    company_ids = fields.Many2many(
        'res.company', string='Companies to Consolidate', required=True,
        default=lambda self: self.env.companies
    )
    line_ids = fields.One2many(
        'ecs.consolidated.cash.position.line', 'wizard_id', string='Cash & Bank Journals', readonly=True
    )
    total_cash_balance = fields.Monetary(string='Total Consolidated Cash/Bank', currency_field='company_currency_id')
    company_currency_id = fields.Many2one(
        'res.currency', string='Display Currency',
        default=lambda self: self.env.company.currency_id
    )

    def action_generate_report(self):
        self.ensure_one()
        self.line_ids.unlink()

        lines_to_create = []
        tot_balance = 0.0

        # Query all bank and cash journals across selected companies
        journals = self.env['account.journal'].search([
            ('company_id', 'in', self.company_ids.ids),
            ('type', 'in', ('bank', 'cash'))
        ])

        for journal in journals:
            # Get current balance from odoo's account journal fields or calculate it from account move line
            # Odoo's standard method to get journal balance is the sum of debit-credit on account_id
            account = journal.default_account_id
            balance = 0.0
            if account:
                # Aggregate move lines posted
                move_lines = self.env['account.move.line'].search([
                    ('account_id', '=', account.id),
                    ('move_id.state', '=', 'posted')
                ])
                raw_balance = sum(move_lines.mapped('balance'))
                # Convert to consolidated reporting currency
                balance = journal.company_id.currency_id._convert(
                    raw_balance, self.company_currency_id, self.env.company, fields.Date.today()
                )
            
            tot_balance += balance

            lines_to_create.append((0, 0, {
                'company_id': journal.company_id.id,
                'journal_id': journal.id,
                'currency_id': self.company_currency_id.id,
                'balance': balance,
            }))

        self.write({
            'line_ids': lines_to_create,
            'total_cash_balance': tot_balance
        })

        return {
            'name': _('Consolidated Cash & Bank Position'),
            'type': 'ir.actions.act_window',
            'res_model': 'ecs.consolidated.cash.position',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new'
        }

class EcsConsolidatedCashPositionLine(models.TransientModel):
    _name = 'ecs.consolidated.cash.position.line'
    _description = 'Consolidated Cash Position Line'

    wizard_id = fields.Many2one('ecs.consolidated.cash.position', string='Wizard', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company')
    journal_id = fields.Many2one('account.journal', string='Bank/Cash Account')
    currency_id = fields.Many2one('res.currency', string='Currency')
    balance = fields.Monetary(string='Current Balance', currency_field='currency_id')
