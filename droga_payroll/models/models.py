# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class droga_payroll(models.Model):
#     _name = 'droga_payroll.droga_payroll'
#     _description = 'droga_payroll.droga_payroll'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
