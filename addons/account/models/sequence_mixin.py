# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date
from odoo.tools import frozendict, mute_logger, date_utils

import re
from collections import defaultdict
from psycopg2 import sql, DatabaseError


class SequenceMixin(models.AbstractModel):
    """Mechanism used to have an editable sequence number.

    Be careful of how you use this regarding the prefixes. More info in the
    docstring of _get_last_sequence.
    """

    _name = 'sequence.mixin'
    _description = "Automatic sequence"

    _sequence_field = "name"
    _sequence_date_field = "date"
    _sequence_index = False
    _sequence_year_range_regex = r'^(?:(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))(?P<prefix2>\D)(?P<year_end>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))(?P<prefix3>\D+?))?(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_monthly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))(?P<prefix2>\D*?)(?P<month>(0[1-9]|1[0-2]))(?P<prefix3>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_yearly_regex = r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)?\d{2}))(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$'
    _sequence_fixed_regex = r'^(?P<prefix1>.*?)(?P<seq>\d{0,9})(?P<suffix>\D*?)$'

    sequence_prefix = fields.Char(compute='_compute_split_sequence', store=True)
    sequence_number = fields.Integer(compute='_compute_split_sequence', store=True)

    def init(self):
        # Add an index to optimise the query searching for the highest sequence number
        if not self._abstract and self._sequence_index:
            index_name = self._table + '_sequence_index'
            self.env.cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', (index_name,))
            if not self.env.cr.fetchone():
                self.env.cr.execute(sql.SQL("""
                    CREATE INDEX {index_name} ON {table} ({sequence_index}, sequence_prefix desc, sequence_number desc, {field});
                    CREATE INDEX {index2_name} ON {table} ({sequence_index}, id desc, sequence_prefix);
                """).format(
                    sequence_index=sql.Identifier(self._sequence_index),
                    index_name=sql.Identifier(index_name),
                    index2_name=sql.Identifier(index_name + "2"),
                    table=sql.Identifier(self._table),
                    field=sql.Identifier(self._sequence_field),
                ))

    def _get_sequence_date_range(self, reset):
        ref_date = fields.Date.to_date(self[self._sequence_date_field])
        if reset in ('year', 'year_range'):
            return (date(ref_date.year, 1, 1), date(ref_date.year, 12, 31))
        if reset == 'month':
            return date_utils.get_month(ref_date)
        if reset == 'never':
            return (date(1, 1, 1), date(9999, 1, 1))
        raise NotImplementedError(reset)

    def _must_check_constrains_date_sequence(self):
        return True

    def _year_match(self, format_value, date):
        return format_value == self._truncate_year_to_length(date.year, len(str(format_value)))

    def _truncate_year_to_length(self, year, length):
        return year % (10 ** length)

    def _sequence_matches_date(self):
        self.ensure_one()
        date = fields.Date.to_date(self[self._sequence_date_field])
        sequence = self[self._sequence_field]

        if not sequence or not date:
            return True

        format_values = self._get_sequence_format_param(sequence)[1]
        sequence_number_reset = self._deduce_sequence_number_reset(sequence)
        year_start, year_end = self._get_sequence_date_range(sequence_number_reset)
        year_match = (
            (not format_values["year"] or self._year_match(format_values["year"], year_start))
            and (not format_values["year_end"] or self._year_match(format_values["year_end"], year_end))
        )
        month_match = not format_values['month'] or format_values['month'] == date.month
        return year_match and month_match

    @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        for record in self:
            if not record._must_check_constrains_date_sequence():
                continue
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if (
                sequence
                and date
                and date > constraint_date
                and not record._sequence_matches_date()
            ):
                raise ValidationError(_(
                    "The %(date_field)s (%(date)s) doesn't match the sequence number of the related %(model)s (%(sequence)s)\n"
                    "You will need to clear the %(model)s's %(sequence_field)s to proceed.\n"
                    "In doing so, you might want to resequence your entries in order to maintain a continuous date-based sequence.",
                    date=format_date(self.env, date),
                    sequence=sequence,
                    date_field=record._fields[record._sequence_date_field]._description_string(self.env),
                    sequence_field=record._fields[record._sequence_field]._description_string(self.env),
                    model=self.env['ir.model']._get(record._name).display_name,
                ))

    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        for record in self:
            sequence = record[record._sequence_field] or ''
            regex = re.sub(r"\?P<\w+>", "?:", record._sequence_fixed_regex.replace(r"?P<seq>", ""))  # make the seq the only matching group
            matching = re.match(regex, sequence)
            record.sequence_prefix = sequence[:matching.start(1)]
            record.sequence_number = int(matching.group(1) or 0)

    @api.model
    def _deduce_sequence_number_reset(self, name):
        """Detect if the used sequence resets yearly, montly or never.

        :param name: the sequence that is used as a reference to detect the resetting
            periodicity. Typically, it is the last before the one you want to give a
            sequence.
        """
        for regex, ret_val, requirements in [
            (self._sequence_monthly_regex, 'month', ['seq', 'month', 'year']),
            (self._sequence_year_range_regex, 'year_range', ['seq', 'year', 'year_end']),
            (self._sequence_yearly_regex, 'year', ['seq', 'year']),
            (self._sequence_fixed_regex, 'never', ['seq']),
        ]:
            match = re.match(regex, name or '')
            if match:
                groupdict = match.groupdict()
                if (
                    groupdict.get('year_end') and groupdict.get('year')
                    and (
                        len(groupdict['year']) < len(groupdict['year_end'])
                        or self._truncate_year_to_length((int(groupdict['year']) + 1), len(groupdict['year_end'])) != int(groupdict['year_end'])
                    )
                ):
                    # year and year_end are not compatible for range (the difference is not 1)
                    continue
                if all(groupdict.get(req) is not None for req in requirements):
                    return ret_val
        raise ValidationError(_(
            'The sequence regex should at least contain the seq grouping keys. For instance:\n'
            r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'
        ))

    def _get_last_sequence_domain(self, relaxed=False):
        """Get the sql domain to retreive the previous sequence number.

        This function should be overriden by models inheriting from this mixin.

        :param relaxed: see _get_last_sequence.

        :returns: tuple(where_string, where_params): with
            where_string: the entire SQL WHERE clause as a string.
            where_params: a dictionary containing the parameters to substitute
                at the execution of the query.
        """
        self.ensure_one()
        return "", {}

    def _get_starting_sequence(self):
        """Get a default sequence number.

        This function should be overriden by models heriting from this mixin
        This number will be incremented so you probably want to start the sequence at 0.

        :return: string to use as the default sequence to increment
        """
        self.ensure_one()
        return "00000000"

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        """Retrieve the previous sequence.

        This is done by taking the number with the greatest alphabetical value within
        the domain of _get_last_sequence_domain. This means that the prefix has a
        huge importance.
        For instance, if you have INV/2019/0001 and INV/2019/0002, when you rename the
        last one to FACT/2019/0001, one might expect the next number to be
        FACT/2019/0002 but it will be INV/2019/0002 (again) because INV > FACT.
        Therefore, changing the prefix might not be convenient during a period, and
        would only work when the numbering makes a new start (domain returns by
        _get_last_sequence_domain is [], i.e: a new year).

        :param field_name: the field that contains the sequence.
        :param relaxed: this should be set to True when a previous request didn't find
            something without. This allows to find a pattern from a previous period, and
            try to adapt it for the new period.
        :param with_prefix: The sequence prefix to restrict the search on, if any.

        :return: the string of the previous sequence or None if there wasn't any.
        """
        self.ensure_one()
        if self._sequence_field not in self._fields or not self._fields[self._sequence_field].store:
            raise ValidationError(_('%s is not a stored field', self._sequence_field))
        where_string, param = self._get_last_sequence_domain(relaxed)
        if self._origin.id:
            where_string += " AND id != %(id)s "
            param['id'] = self._origin.id
        if with_prefix is not None:
            where_string += " AND sequence_prefix = %(with_prefix)s "
            param['with_prefix'] = with_prefix

        query = f"""
                SELECT {self._sequence_field} FROM {self._table}
                {where_string}
                AND sequence_prefix = (SELECT sequence_prefix FROM {self._table} {where_string} ORDER BY id DESC LIMIT 1)
                ORDER BY sequence_number DESC
                LIMIT 1
        """

        self.flush_model([self._sequence_field, 'sequence_number', 'sequence_prefix'])
        self.env.cr.execute(query, param)
        return (self.env.cr.fetchone() or [None])[0]

    def _get_sequence_format_param(self, previous):
        """Get the python format and format values for the sequence.

        :param previous: the sequence we want to extract the format from
        :return tuple(format, format_values):
            format is the format string on which we should call .format()
            format_values is the dict of values to format the `format` string
            ``format.format(**format_values)`` should be equal to ``previous``
        """
        sequence_number_reset = self._deduce_sequence_number_reset(previous)
        regex = self._sequence_fixed_regex
        if sequence_number_reset == 'year':
            regex = self._sequence_yearly_regex
        elif sequence_number_reset == 'year_range':
            regex = self._sequence_year_range_regex
        elif sequence_number_reset == 'month':
            regex = self._sequence_monthly_regex
        format_values = re.match(regex, previous).groupdict()
        format_values['seq_length'] = len(format_values['seq'])
        format_values['year_length'] = len(format_values.get('year') or '')
        format_values['year_end_length'] = len(format_values.get('year_end') or '')
        if not format_values.get('seq') and 'prefix1' in format_values and 'suffix' in format_values:
            # if we don't have a seq, consider we only have a prefix and not a suffix
            format_values['prefix1'] = format_values['suffix']
            format_values['suffix'] = ''
        for field in ('seq', 'year', 'month', 'year_end'):
            format_values[field] = int(format_values.get(field) or 0)

        placeholders = re.findall(r'\b(prefix\d|seq|suffix\d?|year|year_end|month)\b', regex)
        format = ''.join(
            "{seq:0{seq_length}d}" if s == 'seq' else
            "{month:02d}" if s == 'month' else
            "{year:0{year_length}d}" if s == 'year' else
            "{year_end:0{year_end_length}d}" if s == 'year_end' else
            "{%s}" % s
            for s in placeholders
        )
        return format, format_values

    def _set_next_sequence(self):
        """Set the next sequence.

        This method ensures that the field is set both in the ORM and in the database.
        This is necessary because we use a database query to get the previous sequence,
        and we need that query to always be executed on the latest data.

        :param field_name: the field that contains the sequence.
        """
        self.ensure_one()
        last_sequence = self._get_last_sequence()
        new = not last_sequence
        if new:
            last_sequence = self._get_last_sequence(relaxed=True) or self._get_starting_sequence()

        format_string, format_values = self._get_sequence_format_param(last_sequence)
        sequence_number_reset = self._deduce_sequence_number_reset(last_sequence)
        if new:
            date_start, date_end = self._get_sequence_date_range(sequence_number_reset)
            format_values['seq'] = 0
            format_values['year'] = self._truncate_year_to_length(date_start.year, format_values['year_length'])
            format_values['year_end'] = self._truncate_year_to_length(date_end.year, format_values['year_end_length'])
            format_values['month'] = date_start.month

        # before flushing inside the savepoint (which may be rolled back!), make sure everything
        # is already flushed, otherwise we could lose non-sequence fields values, as the ORM believes
        # them to be flushed.
        self.flush_recordset()
        # because we are flushing, and because the business code might be flushing elsewhere (i.e. to
        # validate constraints), the fields depending on the sequence field might be protected by the
        # ORM. This is not desired, so we already reset them here.
        registry = self.env.registry
        triggers = registry._field_triggers[self._fields[self._sequence_field]]
        for inverse_field, triggered_fields in triggers.items():
            for triggered_field in triggered_fields:
                if not triggered_field.store or not triggered_field.compute:
                    continue
                for field in registry.field_inverses[inverse_field[0]] if inverse_field else [None]:
                    self.env.add_to_compute(triggered_field, self[field.name] if field else self)
        while True:
            format_values['seq'] = format_values['seq'] + 1
            sequence = format_string.format(**format_values)
            try:
                with self.env.cr.savepoint(flush=False), mute_logger('odoo.sql_db'):
                    self[self._sequence_field] = sequence
                    self.flush_recordset([self._sequence_field])
                    break
            except DatabaseError as e:
                # 23P01 ExclusionViolation
                # 23505 UniqueViolation
                if e.pgcode not in ('23P01', '23505'):
                    raise
        self._compute_split_sequence()
        self.flush_recordset(['sequence_prefix', 'sequence_number'])

    def _is_last_from_seq_chain(self):
        """Tells whether or not this element is the last one of the sequence chain.

        :return: True if it is the last element of the chain.
        """
        last_sequence = self._get_last_sequence(with_prefix=self.sequence_prefix)
        if not last_sequence:
            return True
        seq_format, seq_format_values = self._get_sequence_format_param(last_sequence)
        seq_format_values['seq'] += 1
        return seq_format.format(**seq_format_values) == self.name

    def _is_end_of_seq_chain(self):
        """Tells whether or not these elements are the last ones of the sequence chain.

        :return: True if self are the last elements of the chain.
        """
        batched = defaultdict(lambda: {'last_rec': self.browse(), 'seq_list': []})
        for record in self.filtered(lambda x: x[x._sequence_field]):
            seq_format, format_values = record._get_sequence_format_param(record[record._sequence_field])
            seq = format_values.pop('seq')
            batch = batched[(seq_format, frozendict(format_values))]
            batch['seq_list'].append(seq)
            if batch['last_rec'].sequence_number <= record.sequence_number:
                batch['last_rec'] = record

        for values in batched.values():
            # The sequences we are deleting are not sequential
            seq_list = values['seq_list']
            if max(seq_list) - min(seq_list) != len(seq_list) - 1:
                return False

            # last_rec must have the highest number in the database
            record = values['last_rec']
            if not record._is_last_from_seq_chain():
                return False
        return True
