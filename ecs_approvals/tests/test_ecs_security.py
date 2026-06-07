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

    def test_seeded_document_types_exist(self):
        document_types = self.env['ecs.approval.document.type'].search([])
        codes = set(document_types.mapped('code'))
        self.assertIn('PAYMENT_REQUEST', codes)
        self.assertIn('PURCHASE_REQUEST', codes)
        self.assertIn('COMPANY_PROFILE', codes)

    def test_seeded_approval_policy_has_steps(self):
        policy = self.env.ref('ecs_approvals.policy_payment_request_import_export')
        self.assertEqual(policy.company_id, self.env.ref('ecs_approvals.company_import_export'))
        self.assertGreaterEqual(policy.step_count, 2)
        self.assertEqual(policy.line_ids.sorted('level')[0].group_id, self.env.ref('ecs_approvals.group_ecs_finance_controller'))

    def test_company_module_scope_tracks_required_modules(self):
        scope = self.env.ref('ecs_approvals.scope_import_export_finance')
        self.assertTrue(scope.required)
        self.assertEqual(scope.company_id, self.env.ref('ecs_approvals.company_import_export'))
        self.assertIn(scope.state, ('ready', 'missing'))
