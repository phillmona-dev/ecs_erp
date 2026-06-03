# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged('ecs', 'ecs_approvals', 'post_install', '-at_install')
class TestEcsApprovals(TransactionCase):

    def test_seeded_company_profiles_exist(self):
        profiles = self.env['ecs.company.profile'].search([])
        codes = set(profiles.mapped('company_code'))
        self.assertIn('import_export', codes)
        self.assertIn('construction', codes)
        self.assertIn('school', codes)

    def test_company_profile_scope_flags(self):
        import_profile = self.env.ref('ecs_approvals.profile_import_export')
        construction_profile = self.env.ref('ecs_approvals.profile_construction')
        school_profile = self.env.ref('ecs_approvals.profile_private_school')
        self.assertTrue(import_profile.requires_sales)
        self.assertFalse(import_profile.requires_project)
        self.assertTrue(construction_profile.requires_project)
        self.assertFalse(construction_profile.requires_sales)
        self.assertTrue(school_profile.requires_school_operations)
        self.assertFalse(school_profile.requires_sales)
        self.assertFalse(school_profile.requires_project)

    def test_owner_group_implies_company_manager(self):
        owner = self.env.ref('ecs_approvals.group_ecs_owner')
        company_manager = self.env.ref('ecs_approvals.group_ecs_company_manager')
        multi_company = self.env.ref('base.group_multi_company')
        self.assertIn(company_manager, owner.implied_ids)
        self.assertIn(multi_company, owner.implied_ids)
