# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportSession(TestPoSCommon):

    def setUp(self):
        super(TestReportSession, self).setUp()
        self.config = self.basic_config

    def test_report_session(self):

        self.tax1 = self.env['account.tax'].create({
            'name': 'Tax 1',
            'amount': 10,
            'price_include': True,
        })
        self.product1 = self.create_product('Product A', self.categ_basic, 110, self.tax1.id)

        self.config.open_ui()
        session_id = self.config.current_session_id.id
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session_id,
            'partner_id': self.partner_a.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 110,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, [self.tax1.id]]],
                'price_subtotal': 100,
                'price_subtotal_incl': 110,
            })],
            'pricelist_id': self.config.pricelist_id.id,
            'amount_paid': 110.0,
            'amount_total': 110.0,
            'amount_tax': 10.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}',
            'to_invoice': False,
        })

        self.make_payment(order, self.bank_split_pm1, 60)
        self.make_payment(order, self.bank_pm1, 50)

        self.config.current_session_id.action_pos_session_closing_control(bank_payment_method_diffs={self.bank_split_pm1.id: 50, self.bank_pm1.id: 40})

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details(session_ids=[session_id])
        split_payment_bank = [p for p in report['payments'] if p.get('id', 0) == self.bank_split_pm1.id]
        self.assertEqual(split_payment_bank[0]['cash_moves'][0]['amount'], 50)
        bank_payment = [p for p in report['payments'] if p.get('id', 0) == self.bank_pm1.id]
        self.assertEqual(bank_payment[0]['cash_moves'][0]['amount'], 40)
        self.assertEqual(report['products'][0]['products'][0]['base_amount'], 100, "Base amount of product should be 100, as we want price without tax")

    def test_report_session_2(self):

        self.product1 = self.create_product('Product A', self.categ_basic, 100)

        self.config.open_ui()
        session_id_1 = self.config.current_session_id.id
        order_info = {'company_id': self.env.company.id,
                      'session_id': session_id_1,
                      'partner_id': self.partner_a.id,
                      'lines': [(0, 0, {
                          'name': "OL/0001",
                          'product_id': self.product1.id,
                          'price_unit': 100,
                          'discount': 0,
                          'qty': 1,
                          'tax_ids': [],
                          'price_subtotal': 100,
                          'price_subtotal_incl': 100,
                      })],
                      'pricelist_id': self.config.pricelist_id.id,
                      'amount_paid': 100.0,
                      'amount_total': 100.0,
                      'amount_tax': 0.0,
                      'amount_return': 0.0,
                      'to_invoice': False,
                      }

        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 100)

        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.cash_pm1, 100)

        self.config.current_session_id.action_pos_session_closing_control()

        self.config.open_ui()
        session_id_2 = self.config.current_session_id.id
        order_info['session_id'] = session_id_2
        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 100)

        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.cash_pm1, 100)

        self.config.current_session_id.action_pos_session_closing_control()

        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        for payment in report['payments']:
            session_name = self.env['pos.session'].browse(payment['session']).name
            payment_method_name = self.env['pos.payment.method'].browse(payment['id']).name
            self.assertEqual(payment['name'], payment_method_name + " " + session_name)

    def test_report_session_3(self):
        self.product1 = self.create_product('Product A', self.categ_basic, 100)
        self.config.open_ui()
        session_id = self.config.current_session_id.id
        order_info = {'company_id': self.env.company.id,
                'session_id': session_id,
                'partner_id': self.partner_a.id,
                'lines': [(0, 0, {
                    'name': "OL/0001",
                    'product_id': self.product1.id,
                    'price_unit': 100,
                    'discount': 0,
                    'qty': 14.9,
                    'tax_ids': [],
                    'price_subtotal': 100,
                    'price_subtotal_incl': 100,
                })],
                'pricelist_id': self.config.pricelist_id.id,
                'amount_paid': 100.0,
                'amount_total': 100.0,
                'amount_tax': 0.0,
                'amount_return': 0.0,
                'to_invoice': False,
                }
        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 100)
        order_info['lines'][0][2]['qty'] =  59.7
        order = self.env['pos.order'].create(order_info)
        self.make_payment(order, self.bank_pm1, 100)
        self.config.current_session_id.action_pos_session_closing_control()
        report = self.env['report.point_of_sale.report_saledetails'].get_sale_details()
        self.assertEqual(report['products'][0]['products'][0]['quantity'], 74.6, "Quantity of product should be 74.6, as we want the sum of the quantity of the two orders")
