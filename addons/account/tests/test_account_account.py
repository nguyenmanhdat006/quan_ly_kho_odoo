# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger
import psycopg2
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestAccountAccount(AccountTestInvoicingCommon):

    def test_changing_account_company(self):
        ''' Ensure you can't change the company of an account.account if there are some journal entries '''

        self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'name': 'line_debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
                (0, 0, {
                    'name': 'line_credit',
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ],
        })

        with self.assertRaises(UserError), self.cr.savepoint():
            self.company_data['default_account_revenue'].company_id = self.company_data_2['company']

    def test_toggle_reconcile(self):
        ''' Test the feature when the user sets an account as reconcile/not reconcile with existing journal entries. '''
        account = self.company_data['default_account_revenue']

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'amount_currency': -200.0,
                }),
            ],
        })
        move.action_post()
        self.env['account.move.line'].flush_model()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

        # Set the account as reconcile and fully reconcile something.
        account.reconcile = True
        self.env.invalidate_all()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 100.0, 'amount_residual_currency': 200.0},
            {'reconciled': False, 'amount_residual': -100.0, 'amount_residual_currency': -200.0},
        ])

        move.line_ids.reconcile()
        self.assertRecordValues(move.line_ids, [
            {'reconciled': True, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': True, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

        # Set back to a not reconcile account and check the journal items.
        move.line_ids.remove_move_reconcile()
        account.reconcile = False
        self.env.invalidate_all()

        self.assertRecordValues(move.line_ids, [
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
            {'reconciled': False, 'amount_residual': 0.0, 'amount_residual_currency': 0.0},
        ])

    def test_toggle_reconcile_with_partials(self):
        ''' Test the feature when the user sets an account as reconcile/not reconcile with partial reconciliation. '''
        account = self.company_data['default_account_revenue']

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                    'amount_currency': 200.0,
                }),
                (0, 0, {
                    'account_id': account.id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 50.0,
                    'amount_currency': -100.0,
                }),
                (0, 0, {
                    'account_id': self.company_data['default_account_expense'].id,
                    'currency_id': self.currency_data['currency'].id,
                    'debit': 0.0,
                    'credit': 50.0,
                    'amount_currency': -100.0,
                }),
            ],
        })
        move.action_post()

        # Set the account as reconcile and partially reconcile something.
        account.reconcile = True

        move.line_ids.filtered(lambda line: line.account_id == account).reconcile()

        # Try to set the account as a not-reconcile one.
        with self.assertRaises(UserError), self.cr.savepoint():
            account.reconcile = False

    def test_toggle_reconcile_outstanding_account(self):
        ''' Test the feature when the user sets an account as not reconcilable when a journal
        is configured with this account as the payment credit or debit account.
        Since such an account should be reconcilable by nature, a ValidationError is raised.'''
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.company_data['default_journal_bank'].company_id.account_journal_payment_debit_account_id.reconcile = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.company_data['default_journal_bank'].company_id.account_journal_payment_credit_account_id.reconcile = False

    def test_remove_account_from_account_group(self):
        """Test if an account is well removed from account group"""
        group = self.env['account.group'].create({
            'name': 'test_group',
            'code_prefix_start': 401000,
            'code_prefix_end': 402000,
            'company_id': self.env.company.id
        })

        account_1 = self.company_data['default_account_revenue'].copy({'code': 401000})
        account_2 = self.company_data['default_account_revenue'].copy({'code': 402000})

        self.assertRecordValues(account_1 + account_2, [{'group_id': group.id}] * 2)

        group.code_prefix_end = 401000

        self.assertRecordValues(account_1 + account_2, [{'group_id': group.id}, {'group_id': False}])

    def test_name_create(self):
        """name_create should only be possible when importing
           Code and Name should be split
        """
        with self.assertRaises(UserError):
            self.env['account.account'].name_create('550003 Existing Account')
        # account code is mandatory and providing a name without a code should raise an error
        with self.assertRaises(psycopg2.DatabaseError), mute_logger('odoo.sql_db'):
            self.env['account.account'].with_context(import_file=True).name_create('Existing Account')
        account_id = self.env['account.account'].with_context(import_file=True).name_create('550003 Existing Account')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550003")
        self.assertEqual(account.name, "Existing Account")

    def test_compute_account_type(self):
        existing_account = self.company_data['default_account_revenue']
        # account_type should be computed
        new_account_code = self.env['account.account']._search_new_account_code(
            company=existing_account.company_id,
            digits=len(existing_account.code),
            prefix=existing_account.code[:-1])
        new_account = self.env['account.account'].create({
            'code': new_account_code,
            'name': 'A new account'
        })
        self.assertEqual(new_account.account_type, existing_account.account_type)
        # account_type should not be altered
        alternate_account = self.env['account.account'].search([('account_type', '!=', existing_account.account_type)], limit=1)
        alternate_code = self.env['account.account']._search_new_account_code(
            company=alternate_account.company_id,
            digits=len(alternate_account.code),
            prefix=alternate_account.code[:-1])
        new_account.code = alternate_code
        self.assertEqual(new_account.account_type, existing_account.account_type)

    def test_compute_current_balance(self):
        """ Test if an account's current_balance is computed correctly """

        account_payable = self.company_data['default_account_payable']
        account_receivable = self.company_data['default_account_receivable']

        payable_debit_move = {
            'line_ids': [
                (0, 0, {'name': 'debit', 'account_id': account_payable.id, 'debit': 100.0, 'credit': 0.0}),
                (0, 0, {'name': 'credit', 'account_id': account_receivable.id, 'debit': 0.0, 'credit': 100.0}),
            ],
        }
        payable_credit_move = {
            'line_ids': [
                (0, 0, {'name': 'credit', 'account_id': account_payable.id, 'debit': 0.0, 'credit': 100.0}),
                (0, 0, {'name': 'debit', 'account_id': account_receivable.id, 'debit': 100.0, 'credit': 0.0}),
            ],
        }

        self.assertEqual(account_payable.current_balance, 0)

        self.env['account.move'].create(payable_debit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, 100)

        self.env['account.move'].create(payable_credit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, 0)

        self.env['account.move'].create(payable_credit_move).action_post()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100)

        self.env['account.move'].create(payable_credit_move).button_cancel()
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100, 'Canceled invoices/bills should not be used when computing the balance')

        # draft invoice
        self.env['account.move'].create(payable_credit_move)
        account_payable._compute_current_balance()
        self.assertEqual(account_payable.current_balance, -100, 'Draft invoices/bills should not be used when computing the balance')

    def test_name_create_account_code_only(self):
        """
        Test account creation with only a code, with and without space
        """
        account_id = self.env['account.account'].with_context(import_file=True).name_create('550003')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550003")
        self.assertEqual(account.name, "")

        account_id = self.env['account.account'].with_context(import_file=True).name_create('550004 ')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550004")
        self.assertEqual(account.name, "")

    def test_name_create_account_name_with_number(self):
        """
        Test the case when a code is provided and the account name contains a number in the first word
        """
        account_id = self.env['account.account'].with_context(import_file=True).name_create('550005 CO2')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "550005")
        self.assertEqual(account.name, "CO2")

        account_id = self.env['account.account'].with_context(import_file=True, default_account_type='expense').name_create('CO2')[0]
        account = self.env['account.account'].browse(account_id)
        self.assertEqual(account.code, "CO2")
        self.assertEqual(account.name, "")

    def test_create_account(self):
        """
        Test creating an account with code and name without name_create
        """
        account = self.env['account.account'].create({
            'code': '314159',
            'name': 'A new account',
            'account_type': 'expense',
        })
        self.assertEqual(account.code, "314159")
        self.assertEqual(account.name, "A new account")

        # name split is only possible through name_create, so an error should be raised
        with self.assertRaises(psycopg2.DatabaseError), mute_logger('odoo.sql_db'):
            account = self.env['account.account'].create({
                'name': '314159 A new account',
                'account_type': 'expense',
            })

        # it doesn't matter whether the account name contains numbers or not
        account = self.env['account.account'].create({
            'code': '31415',
            'name': 'CO2-contributions',
            'account_type': 'expense'
        })
        self.assertEqual(account.code, "31415")
        self.assertEqual(account.name, "CO2-contributions")

    def test_account_name_onchange(self):
        """
        Test various scenarios when creating an account via a form
        """
        account_form = Form(self.env['account.account'])
        account_form.name = "A New Account 1"

        # code should not be set
        self.assertEqual(account_form.code, False)
        self.assertEqual(account_form.name, "A New Account 1")

        account_form.name = "314159 A New Account"
        # the name should be split into code and name
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "A New Account")

        account_form.code = False
        account_form.name = "314159 "
        # the name should be moved to code
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "")

        account_form.code = "314159"
        account_form.name = "CO2-contributions"
        # the name should not overwrite the code
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "CO2-contributions")

        account_form.code = False
        account_form.name = "CO2-contributions"
        # the name should overwrite the code
        self.assertEqual(account_form.code, "CO2-contributions")
        self.assertEqual(account_form.name, "")

        # should save the account correctly
        account_form.code = False
        account_form.name = "314159"
        account = account_form.save()
        self.assertEqual(account.code, "314159")
        self.assertEqual(account.name, "")

        # can change the name of an existing account without overwriting the code
        account_form.name = "123213 Test"
        self.assertEqual(account_form.code, "314159")
        self.assertEqual(account_form.name, "123213 Test")

        account_form.code = False
        account_form.name = "Only letters"
        # saving a form without a code should not be possible
        with self.assertRaises(AssertionError):
            account_form.save()

    @freeze_time('2023-09-30')
    def test_generate_account_suggestions(self):
        """
            Test the generation of account suggestions for a partner.

            - Creates: partner and a account move of that partner.
            - Checks if the most frequent account for the partner matches created account (with recent move).
            - Sets the account as deprecated and checks that it no longer appears in the suggestions.

            * since tested function takes into account last 2 years, we use freeze_time
        """
        partner = self.env['res.partner'].create({'name': 'partner_test_generate_account_suggestions'})
        account = self.company_data['default_account_revenue']
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '2023-09-30',
            'line_ids': [Command.create({'price_unit': 100, 'account_id': account.id})]
        })

        results_1 = self.env['account.account']._get_most_frequent_accounts_for_partner(
            company_id=self.env.company.id,
            partner_id=partner.id,
            move_type="out_invoice"
        )
        self.assertEqual(account.id, results_1[0], "Account with most account_moves should be listed first")

        account.deprecated = True
        account.flush_recordset(['deprecated'])
        results_2 = self.env['account.account']._get_most_frequent_accounts_for_partner(
            company_id=self.env.company.id,
            partner_id=partner.id,
            move_type="out_invoice"
        )
        self.assertFalse(account.id in results_2, "Deprecated account should NOT appear in account suggestions")

    @freeze_time('2017-01-01')
    def test_account_opening_balance(self):
        company = self.env.company
        account = self.company_data['default_account_revenue']
        balancing_account = company.get_unaffected_earnings_account()

        self.assertFalse(company.account_opening_move_id)

        account.opening_debit = 300
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 300.0},
            {'account_id': balancing_account.id,    'balance': -300.0},
        ])

        account.opening_credit = 500
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 300.0},
            {'account_id': account.id,              'balance': -500.0},
            {'account_id': balancing_account.id,    'balance': 200.0},
        ])

        account.opening_balance = 0
        self.cr.precommit.run()
        self.assertFalse(company.account_opening_move_id.line_ids)

        account.currency_id = self.currency_data['currency']
        account.opening_debit = 100
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': balancing_account.id,    'balance': -100.0,  'amount_currency': -100.0},
        ])

        company.account_opening_move_id.write({'line_ids': [
            Command.create({
                'account_id': account.id,
                'balance': 100.0,
                'amount_currency': 200.0,
                'currency_id': account.currency_id.id,
            }),
            Command.create({
                'account_id': balancing_account.id,
                'balance': -100.0,
            }),
        ]})
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': balancing_account.id,    'balance': -100.0,  'amount_currency': -100.0},
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': balancing_account.id,    'balance': -100.0,  'amount_currency': -100.0},
        ])

        account.opening_credit = 1000
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': account.id,              'balance': 100.0,   'amount_currency': 200.0},
            {'account_id': account.id,              'balance': -1000.0, 'amount_currency': -2000.0},
            {'account_id': balancing_account.id,    'balance': 800.0,   'amount_currency': 800.0},
        ])

        account.opening_debit = 1000
        self.cr.precommit.run()
        self.assertRecordValues(company.account_opening_move_id.line_ids.sorted(), [
            # pylint: disable=bad-whitespace
            {'account_id': account.id,              'balance': 1000.0,  'amount_currency': 2000.0},
            {'account_id': account.id,              'balance': -1000.0, 'amount_currency': -2000.0},
        ])

    def test_account_group_hierarchy_consistency(self):
        """ Test if the hierarchy of account groups is consistent when creating, deleting and recreating an account group """
        def create_account_group(name, code_prefix, company):
            return self.env['account.group'].create({
                'name': name,
                'code_prefix_start': code_prefix,
                'code_prefix_end': code_prefix,
                'company_id': company.id
            })

        group_1 = create_account_group('group_1', 1, self.env.company)
        group_10 = create_account_group('group_10', 10, self.env.company)
        group_100 = create_account_group('group_100', 100, self.env.company)
        group_101 = create_account_group('group_101', 101, self.env.company)

        self.assertEqual(len(group_1.parent_id), 0)
        self.assertEqual(group_10.parent_id, group_1)
        self.assertEqual(group_100.parent_id, group_10)
        self.assertEqual(group_101.parent_id, group_10)

        # Delete group_101 and recreate it
        group_101.unlink()
        group_101 = create_account_group('group_101', 101, self.env.company)

        self.assertEqual(len(group_1.parent_id), 0)
        self.assertEqual(group_10.parent_id, group_1)
        self.assertEqual(group_100.parent_id, group_10)
        self.assertEqual(group_101.parent_id, group_10)

        # The root becomes a child and vice versa
        group_3 = create_account_group('group_3', 3, self.env.company)
        group_31 = create_account_group('group_31', 31, self.env.company)
        group_3.code_prefix_start = 312
        self.assertEqual(len(group_31.parent_id), 0)
        self.assertEqual(group_3.parent_id, group_31)

    def test_muticompany_account_groups(self):
        """
            Ensure that account groups are always in a root company
            Ensure that accounts and account groups from a same company tree match
        """

        branch_company = self.env['res.company'].create({
            'name': 'Branch Company',
            'parent_id': self.env.company.id,
        })

        parent_group = self.env['account.group'].create({
            'name': 'Parent Group',
            'code_prefix_start': '123',
            'code_prefix_end': '124'
        })
        child_group = self.env['account.group'].with_company(branch_company).create({
            'name': 'Child Group',
            'code_prefix_start': '125',
            'code_prefix_end': '126',
        })
        self.assertEqual(
            child_group.company_id,
            child_group.company_id.root_id,
            "company_id should never be a branch company"
        )

        branch_account = self.env['account.account'].with_company(branch_company).create({
            'name': 'Branch Account',
            'code': '1234',
        })
        self.assertEqual(
            branch_account.group_id,
            parent_group,
            "group_id computation should work for accounts that are not in the root company"
        )

        parent_account = self.env['account.account'].create({
            'name': 'Parent Account',
            'code': '1235'
        })
        parent_account.with_company(branch_company).code = '1256'
        self.assertEqual(
            parent_account.with_company(branch_company).group_id,
            child_group,
            "group_id computation should work if company_id is not in self.env.companies"
        )
