# -*- coding: utf-8 -*-

from functools import partial
from xmlrpc.client import Fault

from odoo.tests import common, tagged
from odoo.tools.misc import mute_logger


@tagged('-at_install', 'post_install')
class TestError(common.HttpCase):
    def setUp(self):
        super(TestError, self).setUp()
        uid = self.ref("base.user_admin")
        self.rpc = partial(self.xmlrpc_object.execute, common.get_db_name(), uid, "admin")

        # Reset the admin's lang to avoid breaking tests due to admin not in English
        self.rpc("res.users", "write", [uid], {"lang": False})

    def test_01_private(self):
        with self.assertRaisesRegex(Exception, r"Private method"), mute_logger('odoo.http'):
            self.rpc('test_rpc.model_a', '_create')
        with self.assertRaisesRegex(Exception, r"Private method"), mute_logger('odoo.http'):
            self.rpc('test_rpc.model_a', 'private_method')
        with self.assertRaisesRegex(Exception, r"Private method"), mute_logger('odoo.http'):
            self.rpc('test_rpc.model_a', 'init')
        with self.assertRaisesRegex(Exception, r"Private method"), mute_logger('odoo.http'):
            self.rpc('test_rpc.model_a', 'filtered', ['id'])

    def test_01_create(self):
        """ Create: mandatory field not provided """
        self.rpc("test_rpc.model_b", "create", {"name": "B1"})
        try:
            with mute_logger("odoo.sql_db", "odoo.http"):
                self.rpc("test_rpc.model_b", "create", {})
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn("Create/update: a mandatory field is not set.", e.faultString)
            self.assertIn(
                "Delete: another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model B (test_rpc.model_b)", e.faultString)
            self.assertIn("Field: Name (name)", e.faultString)

    def test_02_delete(self):
        """ Delete: NOT NULL and ON DELETE RESTRICT constraints """
        b1 = self.rpc("test_rpc.model_b", "create", {"name": "B1"})
        b2 = self.rpc("test_rpc.model_b", "create", {"name": "B2"})
        self.rpc("test_rpc.model_a", "create", {"name": "A1", "field_b1": b1, "field_b2": b2})

        try:
            with mute_logger("odoo.sql_db", "odoo.http"):
                self.rpc("test_rpc.model_b", "unlink", b1)
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn(
                "another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model A (test_rpc.model_a)", e.faultString)
            self.assertIn("Constraint: test_rpc_model_a_field_b1_fkey", e.faultString)

        # Unlink b2 => ON DELETE RESTRICT constraint raises
        try:
            with mute_logger("odoo.sql_db", "odoo.http"):
                self.rpc("test_rpc.model_b", "unlink", b2)
            raise
        except Exception as e:
            self.assertIn("The operation cannot be completed:", e.faultString)
            self.assertIn(
                " another model requires the record being deleted. If possible, archive it instead.",
                e.faultString,
            )
            self.assertIn("Model: Model A (test_rpc.model_a)", e.faultString)
            self.assertIn("Constraint: test_rpc_model_a_field_b2_fkey", e.faultString)

    def test_03_sql_constraint(self):
        with mute_logger("odoo.sql_db"), mute_logger("odoo.http"):
            with self.assertRaisesRegex(Fault, r'The operation cannot be completed: The value must be positive'):
                self.rpc("test_rpc.model_b", "create", {"name": "B1", "value": -1})
