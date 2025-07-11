# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, warmup


@tagged('company_leave')
class TestCompanyLeave(TransactionCase):
    """ Test leaves for a whole company, conflict resolutions """

    @classmethod
    def setUpClass(cls):
        super(TestCompanyLeave, cls).setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'A company'})
        cls.company.resource_calendar_id.tz = "Europe/Brussels"


        cls.bank_holiday = cls.env['hr.leave.type'].create({
            'name': 'Bank Holiday',
            'responsible_ids': [Command.link(cls.env.ref('base.user_admin').id)],
            'company_id': cls.company.id,
            'requires_allocation': 'no',
        })

        cls.paid_time_off = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'request_unit': 'day',
            'leave_validation_type': 'both',
            'company_id': cls.company.id,
            'requires_allocation': 'no',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'My Employee',
            'company_id': cls.company.id,
            'tz': "Europe/Brussels",
        })

        cls.paid_time_off_hours = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off in Hours',
            'request_unit': 'hour',
            'leave_validation_type': 'no_validation',
            'company_id': cls.company.id,
            'time_type': 'other',
            'requires_allocation': 'yes',
        })

    def test_leave_whole_company_01(self):
        # TEST CASE 1: Leaves taken in days. Take a 3 days leave
        # Add a company leave on the second day.
        # Check that leave is split into 2.

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 9),
        })

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'request_date_from': date(2020, 1, 8),
            'request_date_to': date(2020, 1, 8),
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 4)
        # Original Time Off
        self.assertEqual(leave.state, 'refuse')
        # Before Time Off
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 7, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 7, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'confirm')
        # After Time Off
        self.assertEqual(all_leaves[2].date_from, datetime(2020, 1, 9, 7, 0))
        self.assertEqual(all_leaves[2].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[2].number_of_days, 1)
        self.assertEqual(all_leaves[2].state, 'confirm')
        # Company Time Off
        self.assertEqual(all_leaves[3].date_from, datetime(2020, 1, 8, 7, 0))
        self.assertEqual(all_leaves[3].date_to, datetime(2020, 1, 8, 16, 0))
        self.assertEqual(all_leaves[3].number_of_days, 1)
        self.assertEqual(all_leaves[3].state, 'validate')

    def test_leave_whole_company_02(self):
        # TEST CASE 2: Leaves taken in half-days. Take a 3 days leave
        # Add a company leave on the second day
        # Check that leave is split into 2
        self.paid_time_off.request_unit = 'half_day'

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 9),
        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'request_date_from': date(2020, 1, 8),
            'request_date_to': date(2020, 1, 8),
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 4)
        # Original Time Off
        self.assertEqual(leave.state, 'refuse')
        # Before Time Off
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 7, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 7, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'confirm')
        # After Time Off
        self.assertEqual(all_leaves[2].date_from, datetime(2020, 1, 9, 7, 0))
        self.assertEqual(all_leaves[2].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[2].number_of_days, 1)
        self.assertEqual(all_leaves[2].state, 'confirm')
        # Company Time Off
        self.assertEqual(all_leaves[3].date_from, datetime(2020, 1, 8, 7, 0))
        self.assertEqual(all_leaves[3].date_to, datetime(2020, 1, 8, 16, 0))
        self.assertEqual(all_leaves[3].number_of_days, 1)
        self.assertEqual(all_leaves[3].state, 'validate')

    def test_leave_whole_company_03(self):
        # TEST CASE 3: Time Off taken in half-days. Take a 0.5 days leave
        # Add a company leave on the same day
        # Check that leave refused
        self.paid_time_off.request_unit = 'half_day'

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 7),
            'request_unit_half': True,
            'request_date_from_period': 'am',

        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'request_date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 7),
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 2)
        # Original Time Off
        self.assertEqual(leave.state, 'refuse')
        # Company Time Off
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 7, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 7, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'validate')

    def test_leave_whole_company_04(self):
        # TEST CASE 4: Leaves taken in days. Take a 1 days leave
        # Add a company leave on the same day
        # Check that leave is refused
        self.paid_time_off.request_unit = 'day'

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 9),
            'request_date_to': date(2020, 1, 9),

        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'request_date_from': date(2020, 1, 9),
            'request_date_to': date(2020, 1, 9),
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 2)
        # Original Time Off
        self.assertEqual(leave.state, 'refuse')
        # Company Time Off
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 9, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'validate')

    def test_leave_whole_company_06(self):
        # Test case 6: Leaves taken in days. But the employee
        # only works on Monday, Wednesday and Friday
        # Takes a time off for all the week (3 days), should be split

        self.employee.resource_calendar_id.write({'attendance_ids': [
            (5, 0, 0),
            (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
        ]})

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 6),
            'request_date_to': date(2020, 1, 10),
        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'request_date_from': date(2020, 1, 10),
            'request_date_to': date(2020, 1, 10),
        })
        company_leave._compute_date_from_to()
        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 3)
        # Original Time Off
        self.assertEqual(leave.state, 'refuse')
        # Before Time Off
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 6, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 2)
        self.assertEqual(all_leaves[1].state, 'confirm')
        # Company Time Off
        self.assertEqual(all_leaves[2].date_from, datetime(2020, 1, 10, 7, 0))
        self.assertEqual(all_leaves[2].date_to, datetime(2020, 1, 10, 16, 0))
        self.assertEqual(all_leaves[2].number_of_days, 1)
        self.assertEqual(all_leaves[2].state, 'validate')

    @warmup
    def test_leave_whole_company_07(self):
        # Test Case 7: Try to create a bank holidays for a lot of
        # employees, and check the performances
        # 100 employees - 15 already on holidays that day

        employees = self.env['hr.employee'].create([{
            'name': 'Employee %s' % i,
            'company_id': self.company.id
        } for i in range(100)])

        leaves = self.env['hr.leave'].create([{
            'name': 'Holiday - %s' % employee.name,
            'employee_id': employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 3, 29),
            'request_date_to': date(2020, 4, 1),
        } for employee in employees[0:15]])
        leaves._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'request_date_from': date(2020, 4, 2),
            'request_date_to': date(2020, 4, 2),
        })
        company_leave._compute_date_from_to()

        with self.assertQueryCount(__system__=1856):  # 770 community
            # Original query count: 1987
            # Without tracking/activity context keys: 5154
            company_leave.action_validate()

        leaves = self.env['hr.leave'].search([('holiday_status_id', '=', self.bank_holiday.id)])
        self.assertEqual(len(leaves), 102)

    def test_leave_whole_company_08(self):
        """
            Check leaves given in hours for a company,
            Making sure no leaves are given for 0 Hours / Week employee(i.e. Contractors billed for hours).
        """
        employee_0_test_10, employee_1_test_10, employee_2_test_10 = self.env['hr.employee'].create([{
            'name': 'My Employee 0',
            'company_id': self.company.id,
            'tz': "Europe/Brussels",
        },{
            'name': 'My Employee 1',
            'company_id': self.company.id,
            'tz': "Europe/Brussels",
        },{
            'name': 'My Employee 2',
            'company_id': self.company.id,
            'tz': "Europe/Brussels",
        }])
        zero_hours_working_schedule = self.env['resource.calendar'].create({
            'name': 'Standard - Hours/Week',
            'attendance_ids': [],
            'hours_per_day': 0,
            'tz': "Europe/Brussels",
        })
        employee_0_test_10.resource_calendar_id = zero_hours_working_schedule
        self.env['hr.leave.allocation'].create({
            'name': 'Holiday (8 Hours)',
            'holiday_status_id': self.paid_time_off_hours.id,
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'number_of_days': 1,
        })
        employee_leaves = self.env['hr.leave.allocation'].search([
            ('name', '=', 'Holiday (8 Hours)'),
            ('employee_id', 'in', [employee_0_test_10.id, employee_1_test_10.id, employee_2_test_10.id])])
        self.assertEqual(len(employee_leaves), 2)
