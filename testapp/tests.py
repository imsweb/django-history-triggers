from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.test import TestCase

from history import conf
from history.utils import create_history_table, drop_history_table


class UtilsTests (TestCase):

    def test_create_drop_history_table(self):
        create_history_table(42)
        cursor = connections['default'].cursor()
        cursor.execute("SELECT %(field)s FROM %(table)s" % {
            'table': conf.USER_TEMP_TABLE,
            'field': conf.USER_FIELD,
        })
        self.assertEqual(cursor.fetchone()[0], 42)
        drop_history_table()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '%(table)s')" % {
            'table': conf.USER_TEMP_TABLE,
        })
        self.assertEqual(cursor.fetchone()[0], False)

    def test_drop_no_create(self):
        drop_history_table()
        cursor = connections['default'].cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '%(table)s')" % {
            'table': conf.USER_TEMP_TABLE,
        })
        self.assertEqual(cursor.fetchone()[0], False)


class CommandTests (TestCase):

    def test_add_drop(self):
        call_command('triggers')
        call_command('triggers', drop=True, clear=True)
