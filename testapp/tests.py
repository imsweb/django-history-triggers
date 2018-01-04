from django.conf import settings
from django.db import connections
from django.test import TestCase

from history.utils import create_history_table, drop_history_table


class UtilsTests (TestCase):

    def test_create_drop_history_table(self):
        create_history_table(42)
        table_name = getattr(settings, 'HISTORY_USER_TEMP_TABLE', 'history_user')
        field_name = getattr(settings, 'HISTORY_USER_FIELD', 'user_id')
        cursor = connections['default'].cursor()
        cursor.execute("SELECT %(field)s FROM %(table)s" % {
            'table': table_name,
            'field': field_name,
        })
        self.assertEqual(cursor.fetchone()[0], 42)
        drop_history_table()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '%(table)s')" % {
            'table': table_name,
        })
        self.assertEqual(cursor.fetchone()[0], False)

    def test_drop_no_create(self):
        drop_history_table()
        table_name = getattr(settings, 'HISTORY_USER_TEMP_TABLE', 'history_user')
        cursor = connections['default'].cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '%(table)s')" % {
            'table': table_name,
        })
        self.assertEqual(cursor.fetchone()[0], False)
