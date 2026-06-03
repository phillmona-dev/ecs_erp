# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class EcsConsolidatedPl(models.TransientModel):
    """
    Consolidated Profit & Loss Wizard/Report
    Fetches aggregated values from account.move.line for selected companies and date ranges.
    """
    _name = 'ecs.consolidated.pl'
    _description = 'Consolidated Profit & Loss'

    name = fields.Char(string='Report Title', default='Consolidated P&L')
    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    company_ids = fields.Many2many(
        'res.company', string='Companies to Consolidate', required=True,
        default=lambda self: self.env.companies
    )
    
    line_ids = fields.One2many(
        'ecs.consolidated.pl.line', 'wizard_id', string='P&L Lines', readonly=True
    )
    
    total_revenue = fields.Monetary(string='Total Revenue', currency_field='company_currency_id')
    total_expense = fields.Monetary(string='Total Expense', currency_field='company_currency_id')
    net_profit = fields.Monetary(string='Net Profit / Loss', currency_field='company_currency_id')
    company_currency_id = fields.Many2one(
        'res.currency', string='Display Currency',
        default=lambda self: self.env.company.currency_id
    )

    def action_generate_report(self):
        self.ensure_one()
        # Clear previous lines
        self.line_ids.unlink()

        lines_to_create = []
        
        # Helper to get lines grouped by account type and company
        # We query account.move.line for income and expense accounts
        domain = [
            ('company_id', 'in', self.company_ids.ids),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('account_id.account_type', 'in', ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost'))
        ]
        
        move_lines = self.env['account.move.line'].search(domain)
        
        # Group by company and category (Revenue vs Expense)
        data = {}
        for c in self.company_ids:
            data[c.id] = {
                'revenue': 0.0,
                'expense': 0.0
            }
            
        for ml in move_lines:
            comp_id = ml.company_id.id
            # Determine conversion rate if needed, or simply sum in company currency
            # Since multiple companies might have different currencies, we convert to target display currency
            amount_in_target = ml.company_id.currency_id._convert(
                ml.balance, self.company_currency_id, self.env.company, ml.date or fields.Date.today()
            )
            
            is_income = ml.account_id.account_type in ('income', 'income_other')
            if is_income:
                # Credit balance is negative in Odoo, so we invert it for positive revenue reporting
                data[comp_id]['revenue'] += -amount_in_target
            else:
                data[comp_id]['expense'] += amount_in_target

        tot_rev = 0.0
        tot_exp = 0.0
        
        for comp_id, vals in data.items():
            company = self.env['res.company'].browse(comp_id)
            net = vals['revenue'] - vals['expense']
            tot_rev += vals['revenue']
            tot_exp += vals['expense']
            
            lines_to_create.append((0, 0, {
                'company_id': comp_id,
                'currency_id': self.company_currency_id.id,
                'revenue': vals['revenue'],
                'expense': vals['expense'],
                'net_profit': net,
            }))

        self.write({
            'line_ids': lines_to_create,
            'total_revenue': tot_rev,
            'total_expense': tot_exp,
            'net_profit': tot_rev - tot_exp
        })
        
        # Re-open form view
        return {
            'name': _('Consolidated Profit & Loss'),
            'type': 'ir.actions.act_window',
            'res_model': 'ecs.consolidated.pl',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new'
        }

class EcsConsolidatedPlLine(models.TransientModel):
    _name = 'ecs.consolidated.pl.line'
    _description = 'Consolidated Profit & Loss Line'

    wizard_id = fields.Many2one('ecs.consolidated.pl', string='Wizard', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', string='Currency')
    revenue = fields.Monetary(string='Revenue', currency_field='currency_id')
    expense = fields.Monetary(string='Expense', currency_field='currency_id')
    net_profit = fields.Monetary(string='Net Profit / Loss', currency_field='currency_id')
