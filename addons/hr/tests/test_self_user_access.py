# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from itertools import chain
from lxml import etree

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tests import new_test_user, tagged, Form
from odoo.exceptions import AccessError

@tagged('post_install', '-at_install')
class TestSelfAccessProfile(TestHrCommon):

    def test_access_my_profile(self):
        """ A simple user should be able to read all fields in his profile """
        james = new_test_user(self.env, login='hel', groups='base.group_user', name='Simple employee', email='ric@example.com')
        james = james.with_user(james)
        self.env['hr.employee'].create({
            'name': 'James',
            'user_id': james.id,
            'bank_account_id': self.env['res.partner.bank'].create({'acc_number': 'BE1234567890', 'partner_id': james.partner_id.id}).id
        })
        view = self.env.ref('hr.res_users_view_form_profile')
        view_infos = james.get_view(view.id)
        fields = [el.get('name') for el in etree.fromstring(view_infos['arch']).xpath('//field[not(ancestor::field)]')]
        james.read(fields)

    def test_readonly_fields(self):
        """ Employee related fields should be readonly if self editing is not allowed """
        self.env['ir.config_parameter'].sudo().set_param('hr.hr_employee_self_edit', False)
        james = new_test_user(self.env, login='hel', groups='base.group_user', name='Simple employee', email='ric@example.com')
        james = james.with_user(james)
        self.env['hr.employee'].create({
            'name': 'James',
            'user_id': james.id,
        })

        view = self.env.ref('hr.res_users_view_form_profile')
        fields = james._fields
        view_infos = james.get_view(view.id)
        employee_related_fields = {
            el.get('name')
            for el in etree.fromstring(view_infos['arch']).xpath('//field[not(ancestor::field)]')
            if fields[el.get('name')].related and fields[el.get('name')].related.split('.')[0] == 'employee_id'
        }

        form = Form(james, view=view)
        for field in employee_related_fields:
            with self.assertRaises(AssertionError, msg="Field '%s' should be readonly in the employee profile when self editing is not allowed." % field):
                form.__setattr__(field, 'some value')


    def test_profile_view_fields(self):
        """ A simple user should see all fields in profile view, even if they are protected by groups """
        view = self.env.ref('hr.res_users_view_form_profile')

        # For reference, check the view with user with every groups protecting user fields
        all_groups_xml_ids = chain(*[
            field.groups.split(',')
            for field in self.env['res.users']._fields.values()
            if field.groups
            if field.groups != '.' # "no-access" group on purpose
        ])
        all_groups = self.env['res.groups']
        for xml_id in all_groups_xml_ids:
            all_groups |= self.env.ref(xml_id.strip())
        user_all_groups = new_test_user(self.env, groups='base.group_user', login='hel', name='God')
        user_all_groups.write({'groups_id': [(4, group.id, False) for group in all_groups]})
        view_infos = self.env['res.users'].with_user(user_all_groups).get_view(view.id)
        full_fields = [el.get('name') for el in etree.fromstring(view_infos['arch']).xpath('//field[not(ancestor::field)]')]

        # Now check the view for a simple user
        user = new_test_user(self.env, login='gro', name='Grouillot')
        view_infos = self.env['res.users'].with_user(user).get_view(view.id)
        fields = [el.get('name') for el in etree.fromstring(view_infos['arch']).xpath('//field[not(ancestor::field)]')]

        # Compare both
        self.assertEqual(full_fields, fields, "View fields should not depend on user's groups")

    def test_access_my_profile_toolbar(self):
        """ A simple user shouldn't have the possibilities to see the 'Change Password' action"""
        james = new_test_user(self.env, login='jam', groups='base.group_user', name='Simple employee', email='jam@example.com')
        james = james.with_user(james)
        self.env['hr.employee'].create({
            'name': 'James',
            'user_id': james.id,
        })
        view = self.env.ref('hr.res_users_view_form_profile')
        toolbar = james.get_views([(view.id, 'form')], {'toolbar': True})['views']['form']['toolbar']
        available_actions = toolbar.get('action', [])
        change_password_action = self.env.ref("base.change_password_wizard_action")

        self.assertFalse(any(x['id'] == change_password_action.id for x in available_actions))

        # An ERP manager should have the possibilities to see the 'Change Password'
        john = new_test_user(self.env, login='joh', groups='base.group_erp_manager', name='ERP Manager', email='joh@example.com')
        john = john.with_user(john)
        self.env['hr.employee'].create({
            'name': 'John',
            'user_id': john.id,
        })
        view = self.env.ref('hr.res_users_view_form_profile')
        available_actions = john.get_views([(view.id, 'form')], {'toolbar': True})['views']['form']['toolbar']['action']
        self.assertTrue(any(x['id'] == change_password_action.id for x in available_actions))


class TestSelfAccessRights(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super(TestSelfAccessRights, cls).setUpClass()
        cls.richard = new_test_user(cls.env, login='ric', groups='base.group_user', name='Simple employee', email='ric@example.com')
        cls.richard_emp = cls.env['hr.employee'].create({
            'name': 'Richard',
            'user_id': cls.richard.id,
            'private_phone': '21454',
        })
        cls.hubert = new_test_user(cls.env, login='hub', groups='base.group_user', name='Simple employee', email='hub@example.com')
        cls.hubert_emp = cls.env['hr.employee'].create({
            'name': 'Hubert',
            'user_id': cls.hubert.id,
        })

        cls.protected_fields_emp = OrderedDict([(k, v) for k, v in cls.env['hr.employee']._fields.items() if v.groups == 'hr.group_hr_user'])
        # Compute fields and id field are always readable by everyone
        cls.read_protected_fields_emp = OrderedDict([(k, v) for k, v in cls.env['hr.employee']._fields.items() if not v.compute and k != 'id'])
        cls.self_protected_fields_user = OrderedDict([
            (k, v)
            for k, v in cls.env['res.users']._fields.items()
            if v.groups == 'hr.group_hr_user' and k in cls.env['res.users'].SELF_READABLE_FIELDS
        ])

    # Read hr.employee #
    def testReadSelfEmployee(self):
        with self.assertRaises(AccessError):
            self.hubert_emp.with_user(self.richard).read(self.protected_fields_emp.keys())

    def testReadOtherEmployee(self):
        with self.assertRaises(AccessError):
            self.hubert_emp.with_user(self.richard).read(self.protected_fields_emp.keys())

    # Write hr.employee #
    def testWriteSelfEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.richard_emp.with_user(self.richard).write({f: 'dummy'})

    def testWriteOtherEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.hubert_emp.with_user(self.richard).write({f: 'dummy'})

    # Read res.users #
    def testReadSelfUserEmployee(self):
        for f in self.self_protected_fields_user:
            self.richard.with_user(self.richard).read([f])  # should not raise

    def testReadOtherUserEmployee(self):
        with self.assertRaises(AccessError):
            self.hubert.with_user(self.richard).read(self.self_protected_fields_user)

    # Write res.users #
    def testWriteSelfUserEmployeeSettingFalse(self):
        for f, v in self.self_protected_fields_user.items():
            with self.assertRaises(AccessError):
                self.richard.with_user(self.richard).write({f: 'dummy'})

    def testWriteSelfUserEmployee(self):
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', True)
        for f, v in self.self_protected_fields_user.items():
            val = None
            if v.type == 'char' or v.type == 'text':
                val = '0000' if f == 'pin' else 'dummy'
            if val is not None:
                self.richard.with_user(self.richard).write({f: val})

    def testWriteSelfUserPreferencesEmployee(self):
        # self should always be able to update non hr.employee fields if
        # they are in SELF_READABLE_FIELDS
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', False)
        # should not raise
        vals = [
            {'tz': "Australia/Sydney"},
            {'email': "new@example.com"},
            {'signature': "<p>I'm Richard!</p>"},
            {'notification_type': "email"},
        ]
        for v in vals:
            # should not raise
            self.richard.with_user(self.richard).write(v)

    def testWriteOtherUserPreferencesEmployee(self):
        # self should always be able to update non hr.employee fields if
        # they are in SELF_READABLE_FIELDS
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', False)
        vals = [
            {'tz': "Australia/Sydney"},
            {'email': "new@example.com"},
            {'signature': "<p>I'm Richard!</p>"},
            {'notification_type': "email"},
        ]
        for v in vals:
            with self.assertRaises(AccessError):
                self.hubert.with_user(self.richard).write(v)

    def testWriteSelfPhoneEmployee(self):
        # phone is a related from res.partner (from base) but added in SELF_READABLE_FIELDS
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', False)
        with self.assertRaises(AccessError):
            self.richard.with_user(self.richard).write({'phone': '2154545'})

    def testWriteOtherUserEmployee(self):
        for f in self.self_protected_fields_user:
            with self.assertRaises(AccessError):
                self.hubert.with_user(self.richard).write({f: 'dummy'})

    def testSearchUserEMployee(self):
        # Searching user based on employee_id field should not raise bad query error
        self.env['res.users'].with_user(self.richard).search([('employee_id', 'ilike', 'Hubert')])

    def test_onchange_readable_fields_with_no_access(self):
        """
            The purpose is to test that the onchange logic takes into account `SELF_READABLE_FIELDS`.

            The view contains fields that are in `SELF_READABLE_FIELDS` (example: `private_street`).
            Even if the user does not have read access to the employee,
            it should not cause an access error if these fields are in `SELF_READABLE_FIELDS`.
        """
        self.env['res.lang']._activate_lang("fr_FR")
        with Form(self.richard.with_user(self.richard), view='hr.res_users_view_form_profile') as form:
            # triggering an onchange should not trigger some access error
            form.lang = "fr_FR"
            form.tz = "Europe/Brussels"

    def test_access_employee_account(self):
        hubert = new_test_user(self.env, login='hubert', groups='base.group_user', name='Hubert Bonisseur de La Bath', email='hubert@oss.fr')
        hubert = hubert.with_user(hubert)
        hubert_acc = self.env['res.partner.bank'].create({'acc_number': 'FR1234567890', 'partner_id': hubert.partner_id.id})
        hubert_emp = self.env['hr.employee'].create({
            'name': 'Hubert',
            'user_id': hubert.id,
            'bank_account_id': hubert_acc.id
        })
        hubert.partner_id.sudo().employee_ids = hubert_emp

        self.assertFalse(hubert.user_has_groups('hr.group_hr_user'))
        self.assertFalse(hubert.env.su)

        self.assertEqual(hubert.read(['employee_bank_account_id'])[0]['employee_bank_account_id'][1], 'FR******7890')
        self.assertEqual(hubert.sudo().employee_bank_account_id.display_name, 'FR******7890')
        self.assertEqual(hubert_emp.with_user(hubert).sudo().bank_account_id.display_name, 'FR******7890')

        hubert_acc.invalidate_recordset(["display_name"])
        self.assertEqual(hubert_emp.with_user(hubert).sudo().bank_account_id.sudo(False).display_name, 'FR******7890')
