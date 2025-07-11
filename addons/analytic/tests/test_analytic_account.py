# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import Form, TransactionCase
from odoo import Command
from odoo.exceptions import RedirectWarning


@tagged('post_install', '-at_install')
class TestAnalyticAccount(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create new user to avoid demo data.
        user = cls.env['res.users'].create({
            'name': 'The anal(ytic) expert!',
            'login': 'analytic',
            'password': 'analytic',
            'groups_id': [
                (6, 0, cls.env.user.groups_id.ids),
                (4, cls.env.ref('analytic.group_analytic_accounting').id),
            ],
        })
        user.partner_id.email = 'analyticman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        # This is mandatory to test access rights.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.company_data = cls.env['res.company'].create({
            'name': 'company_data',
        })
        cls.company_b_branch = cls.env['res.company'].create({'name': "B Branch", 'parent_id': cls.company_data.id})
        cls.env.user.company_ids |= cls.company_data + cls.company_b_branch

        user.write({
            'company_ids': [(6, 0, [cls.company_data.id, cls.company_b_branch.id])],
            'company_id': cls.company_data.id,
        })
        cls.analytic_plan_offset = len(cls.env['account.analytic.plan'].get_relevant_plans())

        cls.analytic_plan_1 = cls.env['account.analytic.plan'].create({
            'name': 'Plan 1',
            'default_applicability': 'unavailable',
        })
        cls.analytic_plan_child = cls.env['account.analytic.plan'].create({
            'name': 'Plan Child',
            'parent_id': cls.analytic_plan_1.id,
        })
        cls.analytic_plan_2 = cls.env['account.analytic.plan'].create({
            'name': 'Plan 2',
        })

        cls.partner_a = cls.env['res.partner'].create({'name': 'partner_a', 'company_id': False})
        cls.partner_b = cls.env['res.partner'].create({'name': 'partner_b', 'company_id': False})

        cls.analytic_account_1 = cls.env['account.analytic.account'].create({'name': 'Account 1', 'plan_id': cls.analytic_plan_1.id})
        cls.analytic_account_2 = cls.env['account.analytic.account'].create({'name': 'Account 2', 'plan_id': cls.analytic_plan_child.id})
        cls.analytic_account_3 = cls.env['account.analytic.account'].create({'name': 'Account 3', 'plan_id': cls.analytic_plan_2.id})

        cls.distribution_1 = cls.env['account.analytic.distribution.model'].create({
            'partner_id': cls.partner_a.id,
            'analytic_distribution': {cls.analytic_account_3.id: 100}
        })

        cls.distribution_2 = cls.env['account.analytic.distribution.model'].create({
            'partner_id': cls.partner_b.id,
            'analytic_distribution': {cls.analytic_account_2.id: 100}
        })

    def test_get_plans_without_options(self):
        """ Test that the plans with the good appliability are returned without if no options are given """
        kwargs = {}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json) - self.analytic_plan_offset, "Only the Default plan and the demo data plans should be available")

        self.analytic_plan_1.write({'default_applicability': 'mandatory'})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "All root plans should be available")

    def test_get_plans_with_option(self):
        """ Test the plans returned with applicability rules and options """
        kwargs = {'business_domain': 'general'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json) - self.analytic_plan_offset, "Only the Default plan and the demo data plans should be available")

        applicability = self.env['account.analytic.applicability'].create({
            'business_domain': 'general',
            'analytic_plan_id': self.analytic_plan_1.id,
            'applicability': 'mandatory'
        })
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "All root plans should be available")

        self.analytic_plan_1.write({'default_applicability': 'mandatory'})
        applicability.write({'applicability': 'unavailable'})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(1, len(plans_json) - self.analytic_plan_offset, "Plan 1 should be unavailable")

        kwargs = {'business_domain': 'purchase_order'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "Both plans should be available")

        kwargs = {'applicability': 'optional'}
        plans_json = self.env['account.analytic.plan'].get_relevant_plans(**kwargs)
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset, "All root plans should be available")

    def test_analytic_distribution_model(self):
        """ Test the distribution returned from the distribution model """
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({})
        self.assertEqual(distribution_json, {}, "No distribution should be given")
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_3.id): 100}, "Distribution 1 should be given")
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_b.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_2.id): 100}, "Distribution 2 should be given")

    def test_order_analytic_distribution_model(self):
        """ Test the distribution returned with company field"""
        distribution_3 = self.env['account.analytic.distribution.model'].create({
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_1.id: 100},
            'company_id': self.company_data.id,
        })
        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({})
        self.assertEqual(distribution_json, {}, "No distribution should be given")

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, distribution_3.analytic_distribution,
                         "Distribution 3 should be given, as the company is specified in the model")

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_b.id,
            "company_id": self.company_data.id,
        })
        self.assertEqual(distribution_json, {str(self.analytic_account_2.id): 100},
                         "Distribution 2 should be given, for the partner")

        partner_category = self.env['res.partner.category'].create({'name': 'partner_categ'})
        self.partner_a.write({
            'category_id': [Command.set([partner_category.id])]
        })

        distribution_4 = self.env['account.analytic.distribution.model'].create({
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_1.id: 100, self.analytic_account_2.id: 100},
            'partner_category_id': partner_category.id,
        })

        distribution_json = self.env['account.analytic.distribution.model']._get_distribution({
            "partner_id": self.partner_a.id,
            "company_id": self.company_data.id,
            "partner_category_id": partner_category.ids,
        })
        self.assertEqual(distribution_json, distribution_4.analytic_distribution,
                         "Distribution 4 should be given, as the partner_category_id is better than the company_id")

    def test_analytic_plan_account_child(self):
        """
        Check that when an analytic account is set to the third (or more) child,
        the root plan is correctly retrieved.
        """
        self.analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Parent Plan',
        })
        self.analytic_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Plan',
            'parent_id': self.analytic_plan.id,
        })
        self.analytic_sub_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Sub Plan',
            'parent_id': self.analytic_sub_plan.id,
        })
        self.env['account.analytic.account'].create({'name': 'Account', 'plan_id': self.analytic_plan.id})
        self.env['account.analytic.account'].create({'name': 'Child Account', 'plan_id': self.analytic_sub_plan.id})
        self.env['account.analytic.account'].create({'name': 'Grand Child Account', 'plan_id': self.analytic_sub_sub_plan.id})
        plans_json = self.env['account.analytic.plan'].get_relevant_plans()
        self.assertEqual(2, len(plans_json) - self.analytic_plan_offset,
                         "The parent plan should be available even if the analytic account is set on child of third generation")

    def test_all_account_count_with_subplans(self):
        self.analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Parent Plan',
        })
        self.analytic_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Plan',
            'parent_id': self.analytic_plan.id,
        })
        self.analytic_sub_sub_plan = self.env['account.analytic.plan'].create({
            'name': 'Sub Sub Plan',
            'parent_id': self.analytic_sub_plan.id,
        })

        self.env['account.analytic.account'].create([
            {'name': 'Account', 'plan_id': self.analytic_plan.id},
            {'name': 'Child Account', 'plan_id': self.analytic_sub_plan.id},
            {'name': 'Grand Child Account', 'plan_id': self.analytic_sub_sub_plan.id}
        ])

        expected_values = {self.analytic_plan: 3, self.analytic_sub_plan: 2, self.analytic_sub_sub_plan: 1}
        for plan, expected_value in expected_values.items():
            with self.subTest(plan=plan.name, expected_count=expected_value):
                with Form(plan) as plan_form:
                    self.assertEqual(plan_form.record.all_account_count, expected_value)

    def test_analytic_account_branches(self):
        """
        Test that an analytic account defined in a parent company is accessible in its branches (children)
        """
        # timesheet adds a rule to forcer a project_id; account overrides it
        timesheet_user = self.env.ref('hr_timesheet.group_hr_timesheet_user', raise_if_not_found=False)
        account_user = self.env.ref('account.analytic.model_account_analytic_line', raise_if_not_found=False)
        if timesheet_user and not account_user:
            self.skipTest("`hr_timesheet` overrides analytic rights. Without `account` the test would crash")

        self.analytic_account_1.company_id = self.company_data
        self.env['account.analytic.line'].create({
            'name': 'company specific account',
            'account_id': self.analytic_account_1.id,
            'amount': 100,
            'company_id': self.company_b_branch.id,
        })

    def test_change_plan(self):
        """Changing the plan of an account updates columns of the analytic lines."""
        plan_1_col = self.analytic_plan_1._column_name()
        plan_2_col = self.analytic_plan_2._column_name()
        self.assertNotEqual(plan_1_col, plan_2_col)
        line = self.env['account.analytic.line'].create({
            'name': 'test',
            plan_1_col: self.analytic_account_1.id,
        })
        self.analytic_account_1.plan_id = self.analytic_plan_2
        self.assertRecordValues(line, [{
            plan_1_col: False,
            plan_2_col: self.analytic_account_1.id,
        }])

    def test_change_plan_conflict(self):
        """Don't allow changing the plan if some lines already have values set for that plan."""
        plan_1_col = self.analytic_plan_1._column_name()
        plan_2_col = self.analytic_plan_2._column_name()
        self.assertNotEqual(plan_1_col, plan_2_col)
        self.env['account.analytic.line'].create({
            'name': 'test',
            plan_1_col: self.analytic_account_1.id,
            plan_2_col: self.analytic_account_2.id,
        })
        with self.assertRaisesRegex(RedirectWarning, "wipe out your current data"):
            self.analytic_account_1.plan_id = self.analytic_plan_2

    def test_change_plan_no_conflict(self):
        """Exception for the previous test if it was already the correct value that is set."""
        plan_1_col = self.analytic_plan_1._column_name()
        plan_2_col = self.analytic_plan_2._column_name()
        self.assertNotEqual(plan_1_col, plan_2_col)
        line = self.env['account.analytic.line'].create({
            'name': 'test',
            plan_1_col: self.analytic_account_1.id,
            plan_2_col: self.analytic_account_1.id,
        })
        self.analytic_account_1.plan_id = self.analytic_plan_2
        self.assertRecordValues(line, [{
            plan_1_col: False,
            plan_2_col: self.analytic_account_1.id,
        }])

    def test_change_parent_plan(self):
        """Changing the parent of a plan updates account columns of the analytic lines."""
        plan_1_col = self.analytic_plan_1._column_name()
        plan_2_col = self.analytic_plan_2._column_name()
        line = self.env['account.analytic.line'].create({
            'name': 'test',
            plan_1_col: self.analytic_account_1.id,
        })

        # Setting a parent plan should lead to the line having analytic_account_1 under Plan 2
        self.analytic_plan_1.parent_id = self.analytic_plan_2
        self.assertRecordValues(line, [{
            plan_2_col: self.analytic_account_1.id,
        }])
        # plan_1_col should no longer be a field of the analytic line
        self.assertNotIn(plan_1_col, line)

        # Removing the parent plan should fully reverse the analytic line
        self.analytic_plan_1.parent_id = False
        self.assertRecordValues(line, [{
            plan_1_col: self.analytic_account_1.id,
            plan_2_col: False,
        }])

    def test_change_parent_plan_conflict(self):
        """
        Test case where changing the parent plan leads to more than one account under the same
        plan in an analytic line.
        """
        plan_1_col = self.analytic_plan_1._column_name()
        plan_2_col = self.analytic_plan_2._column_name()
        self.env['account.analytic.line'].create({
            'name': 'test',
            plan_1_col: self.analytic_account_1.id,
            plan_2_col: self.analytic_account_2.id,
        })
        with self.assertRaisesRegex(RedirectWarning, "Making this change would wipe out"):
            self.analytic_plan_1.parent_id = self.analytic_plan_2
