# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_it_edi.tests.common import TestItEdi

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItAccountMoveSend(TestItEdi, TestAccountMoveSendCommon):

    def init_invoice(self, partners):
        invoices = self.env['account.move']
        for partner in partners:
            invoices |= super().init_invoice(
                "out_invoice",
                partner=partner,
                company=self.company,
                amounts=[1000],
                taxes=self.default_tax,
                post=True)
        return invoices

    def get_attachments(self, res_id):
        return self.env['ir.attachment'].with_company(self.company).search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', res_id),
            ('res_field', 'in', ('invoice_pdf_report_file', 'l10n_it_edi_attachment_file')),
        ])

    def test_invoice_multi_without_l10n_it_edi_xml_export(self):
        # Prepare
        invoice1, invoice2 = self.init_invoice(self.italian_partner_a + self.italian_partner_a)
        wizard = self.create_send_and_print(invoice1 + invoice2,
            mode='invoice_multi',
            enable_download=True,
            checkbox_download=True,
            enable_send_mail=True,
            checkbox_send_mail=False,
            l10n_it_edi_enable_xml_export=True,
            l10n_it_edi_checkbox_xml_export=False,
            l10n_it_edi_enable_send=True,
            l10n_it_edi_checkbox_send=False,
        )

        # Process
        results = wizard.action_send_and_print()

        # Asserts
        self.assertEqual((invoice1 + invoice2).mapped('send_and_print_values'), [False, False])
        self.assertEqual(results['type'], 'ir.actions.act_url')
        self.assertEqual(1, len(self.get_attachments(invoice1.id)))
        self.assertTrue(invoice1.invoice_pdf_report_id)
        self.assertFalse(invoice1.l10n_it_edi_attachment_id)
        self.assertFalse(invoice1.is_being_sent)
        self.assertEqual(1, len(self.get_attachments(invoice2.id)))
        self.assertTrue(invoice2.invoice_pdf_report_id)
        self.assertFalse(invoice2.l10n_it_edi_attachment_id)
        self.assertFalse(invoice2.is_being_sent)

    def test_invoice_multi_with_l10n_it_edi_xml_export(self):
        # Prepare
        invoice1, invoice2 = self.init_invoice(self.italian_partner_a + self.italian_partner_a)
        wizard = self.create_send_and_print(invoice1 + invoice2,
            mode='invoice_multi',
            enable_download=True,
            checkbox_download=True,
            enable_send_mail=True,
            checkbox_send_mail=False,
            l10n_it_edi_enable_xml_export=True,
            l10n_it_edi_checkbox_xml_export=True,
            l10n_it_edi_enable_send=True,
            l10n_it_edi_checkbox_send=False,
        )

        # Process
        results = wizard.action_send_and_print()

        # Asserts
        self.assertEqual((invoice1 + invoice2).mapped('send_and_print_values'), [False, False])
        self.assertEqual(results['type'], 'ir.actions.act_url')
        self.assertEqual(2, len(self.get_attachments(invoice1.id)))
        self.assertTrue(invoice1.invoice_pdf_report_id)
        self.assertTrue(invoice1.l10n_it_edi_attachment_id)
        self.assertFalse(invoice1.is_being_sent)
        self.assertEqual(2, len(self.get_attachments(invoice2.id)))
        self.assertTrue(invoice2.invoice_pdf_report_id)
        self.assertTrue(invoice2.l10n_it_edi_attachment_id)
        self.assertFalse(invoice2.is_being_sent)

    def test_invoice_with_cig_or_cup_or_both(self):
            
            self.italian_partner_a.write({'l10n_it_pa_index': '1234567'})
            
            invoice_valid = self.init_invoice(self.italian_partner_a)
            invoice_cig_only = self.init_invoice(self.italian_partner_a)
            invoice_cup_only = self.init_invoice(self.italian_partner_a)
            invoice_cig_cup = self.init_invoice(self.italian_partner_a)

            invoice_valid.write({
                'l10n_it_cig': '1234567',
                'l10n_it_cup': '7654321',
                'l10n_it_origin_document_type': 'purchase_order'
            }) 
            
            invoice_cig_only.write({
                'l10n_it_cig': '1234567',
                'l10n_it_cup': False,
                'l10n_it_origin_document_type': False
            }) 
            
            invoice_cup_only.write({
                'l10n_it_cig': False,
                'l10n_it_cup': '7654321',
                'l10n_it_origin_document_type': False
            })
            
            invoice_cig_cup.write({
                'l10n_it_cig': '1234567',
                'l10n_it_cup': '7654321',
                'l10n_it_origin_document_type': False
            }) 

            valid = invoice_valid._l10n_it_edi_base_export_check()
            cig = invoice_cig_only._l10n_it_edi_base_export_check()
            cup = invoice_cup_only._l10n_it_edi_base_export_check()
            cig_cup = invoice_cig_cup._l10n_it_edi_base_export_check()

            self.assertNotIn('move_missing_origin_document_field', valid)
            self.assertIn('move_missing_origin_document_field', cig)
            self.assertIn('move_missing_origin_document_field', cup)
            self.assertIn('move_missing_origin_document_field', cig_cup)
