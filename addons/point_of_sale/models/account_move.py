# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    pos_order_ids = fields.One2many('pos.order', 'account_move')
    pos_payment_ids = fields.One2many('pos.payment', 'account_move_id')
    pos_refunded_invoice_ids = fields.Many2many('account.move', 'refunded_invoices', 'refund_account_move', 'original_account_move')

    @api.depends('tax_cash_basis_created_move_ids')
    def _compute_always_tax_exigible(self):
        super()._compute_always_tax_exigible()
        # The pos closing move does not create caba entries (anymore); we set the tax values directly on the closing move.
        # (But there may still be old closing moves that used caba entries from previous versions.)
        relevant_moves = self.filtered(lambda move: not (move.always_tax_exigible or move.tax_cash_basis_created_move_ids))
        if not relevant_moves:
            return
        sessions = self.env['pos.session'].with_context(active_test=False).search([
            ('move_id', 'in', relevant_moves.ids),
        ])
        sessions.move_id.always_tax_exigible = True

    def _stock_account_get_last_step_stock_moves(self):
        stock_moves = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'out_invoice'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
        for invoice in self.filtered(lambda x: x.move_type == 'out_refund'):
            stock_moves += invoice.sudo().mapped('pos_order_ids.picking_ids.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'customer')
        return stock_moves


    def _get_invoiced_lot_values(self):
        self.ensure_one()

        lot_values = super(AccountMove, self)._get_invoiced_lot_values()

        if self.state == 'draft':
            return lot_values

        # user may not have access to POS orders, but it's ok if they have
        # access to the invoice
        for order in self.sudo().pos_order_ids:
            for line in order.lines:
                lots = line.pack_lot_ids or False
                if lots:
                    for lot in lots:
                        lot_values.append({
                            'product_name': lot.product_id.name,
                            'quantity': line.qty if lot.product_id.tracking == 'lot' else 1.0,
                            'uom_name': line.product_uom_id.name,
                            'lot_name': lot.lot_name,
                            'pos_lot_id': lot.id,
                        })

        return lot_values

    def _compute_payments_widget_reconciled_info(self):
        """Add pos_payment_name field in the reconciled vals to be able to show the payment method in the invoice."""
        super()._compute_payments_widget_reconciled_info()
        for move in self:
            if move.invoice_payments_widget:
                if move.state == 'posted' and move.is_invoice(include_receipts=True):
                    reconciled_partials = move._get_all_reconciled_invoice_partials()
                    for i, reconciled_partial in enumerate(reconciled_partials):
                        counterpart_line = reconciled_partial['aml']
                        pos_payment = counterpart_line.move_id.sudo().pos_payment_ids
                        move.invoice_payments_widget['content'][i].update({
                            'pos_payment_name': pos_payment.payment_method_id.name,
                        })

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _stock_account_get_anglo_saxon_price_unit(self):
        self.ensure_one()
        if not self.product_id:
            return self.price_unit
        price_unit = super(AccountMoveLine, self)._stock_account_get_anglo_saxon_price_unit()
        sudo_order = self.move_id.sudo().pos_order_ids
        if sudo_order:
            price_unit = sudo_order._get_pos_anglo_saxon_price_unit(self.product_id, self.move_id.partner_id.id, self.quantity)
        return price_unit

    def _check_edi_line_tax_required(self):
        if self.product_id.type == 'combo':
            return False
        return super()._check_edi_line_tax_required()
