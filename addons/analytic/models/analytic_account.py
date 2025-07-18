# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import itertools
from odoo import api, fields, models, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools import groupby, SQL


class AccountAnalyticAccount(models.Model):
    _name = 'account.analytic.account'
    _inherit = ['mail.thread']
    _description = 'Analytic Account'
    _order = 'plan_id, name asc'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of
    _rec_names_search = ['name', 'code']

    name = fields.Char(
        string='Analytic Account',
        index='trigram',
        required=True,
        tracking=True,
        translate=True,
    )
    code = fields.Char(
        string='Reference',
        index='btree',
        tracking=True,
    )
    active = fields.Boolean(
        'Active',
        help="Deactivate the account.",
        default=True,
        tracking=True,
    )
    plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Plan',
        required=True,
    )
    root_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Root Plan',
        related="plan_id.root_id",
        store=True,
    )
    color = fields.Integer(
        'Color Index',
        related='plan_id.color',
    )

    line_ids = fields.One2many(
        'account.analytic.line',
        'auto_account_id',  # magic link to the right column (plan) by using the context in the view
        string="Analytic Lines",
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # use auto_join to speed up name_search call
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        auto_join=True,
        tracking=True,
        check_company=True,
    )

    balance = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Balance',
    )
    debit = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Debit',
    )
    credit = fields.Monetary(
        compute='_compute_debit_credit_balance',
        string='Credit',
    )

    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
    )

    @api.constrains('company_id')
    def _check_company_consistency(self):
        for company, accounts in groupby(self, lambda account: account.company_id):
            if company and self.env['account.analytic.line'].sudo().search_count([
                ('auto_account_id', 'in', [account.id for account in accounts]),
                '!', ('company_id', 'child_of', company.id),
            ], limit=1):
                raise UserError(_("You can't set a different company on your analytic account since there are some analytic items linked to it."))

    @api.depends('code', 'partner_id')
    def _compute_display_name(self):
        for analytic in self:
            name = analytic.name
            if analytic.code:
                name = f'[{analytic.code}] {name}'
            if analytic.partner_id.commercial_partner_id.name:
                name = f'{name} - {analytic.partner_id.commercial_partner_id.name}'
            analytic.display_name = name

    def copy_data(self, default=None):
        default = dict(default or {})
        default.setdefault('name', _("%s (copy)", self.name))
        return super().copy_data(default)

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        """ Override _read_group to aggregate no-store compute: balance/debit/credit """
        SPECIAL = {'balance:sum', 'debit:sum', 'credit:sum'}
        if SPECIAL.isdisjoint(aggregates):
            return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

        base_aggregates = [*(agg for agg in aggregates if agg not in SPECIAL), 'id:recordset']
        base_result = super()._read_group(domain, groupby, base_aggregates, having, offset, limit, order)

        # base_result = [(a1, b1, records), (a2, b2, records), ...]
        result = []
        for *other, records in base_result:
            for index, spec in enumerate(itertools.chain(groupby, aggregates)):
                if spec in SPECIAL:
                    field_name = spec.split(':')[0]
                    other.insert(index, sum(records.mapped(field_name)))
            result.append(tuple(other))

        return result

    @api.depends('line_ids.amount')
    def _compute_debit_credit_balance(self):
        def convert(amount, from_currency):
            return from_currency._convert(
                from_amount=amount,
                to_currency=self.env.company.currency_id,
                company=self.env.company,
                date=fields.Date.today(),
            )

        domain = [('company_id', 'in', [False] + self.env.companies.ids)]
        if self._context.get('from_date', False):
            domain.append(('date', '>=', self._context['from_date']))
        if self._context.get('to_date', False):
            domain.append(('date', '<=', self._context['to_date']))

        for plan, accounts in self.grouped('plan_id').items():
            credit_groups = self.env['account.analytic.line']._read_group(
                domain=domain + [(plan._column_name(), 'in', self.ids), ('amount', '>=', 0.0)],
                groupby=[plan._column_name(), 'currency_id'],
                aggregates=['amount:sum'],
            )
            data_credit = defaultdict(float)
            for account, currency, amount_sum in credit_groups:
                data_credit[account.id] += convert(amount_sum, currency)

            debit_groups = self.env['account.analytic.line']._read_group(
                domain=domain + [(plan._column_name(), 'in', self.ids), ('amount', '<', 0.0)],
                groupby=[plan._column_name(), 'currency_id'],
                aggregates=['amount:sum'],
            )
            data_debit = defaultdict(float)
            for account, currency, amount_sum in debit_groups:
                data_debit[account.id] += convert(amount_sum, currency)

            for account in accounts:
                account.debit = -data_debit.get(account.id, 0.0)
                account.credit = data_credit.get(account.id, 0.0)
                account.balance = account.credit - account.debit

    def _update_accounts_in_analytic_lines(self, new_fname, current_fname, accounts):
        if current_fname != new_fname:
            domain = [
                (new_fname, 'not in', accounts.ids + [False]),
                (current_fname, 'in', accounts.ids),
            ]
            if self.env['account.analytic.line'].sudo().search_count(domain, limit=1):
                list_view = self.env.ref('analytic.view_account_analytic_line_tree', raise_if_not_found=False)
                raise RedirectWarning(
                    message=_("Whoa there! Making this change would wipe out your current data. Let's avoid that, shall we?"),
                    action={
                        'res_model': 'account.analytic.line',
                        'type': 'ir.actions.act_window',
                        'domain': domain,
                        'target': 'new',
                        'views': [(list_view and list_view.id, 'list')]
                    },
                    button_text=_("See them"),
                )
            self.env.cr.execute(SQL(
                """
                UPDATE account_analytic_line
                   SET %(new_fname)s = %(current_fname)s,
                       %(current_fname)s = NULL
                 WHERE %(current_fname)s = ANY(%(account_ids)s)
                """,
                new_fname=SQL.identifier(new_fname),
                current_fname=SQL.identifier(current_fname),
                account_ids=accounts.ids,
            ))
            self.env['account.analytic.line'].invalidate_model()

    def write(self, vals):
        if vals.get('plan_id'):
            new_fname = self.env['account.analytic.plan'].browse(vals['plan_id'])._column_name()
            for plan, accounts in self.grouped('plan_id').items():
                current_fname = plan._column_name()
                self._update_accounts_in_analytic_lines(new_fname, current_fname, accounts)
        return super().write(vals)
