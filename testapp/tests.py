from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.test import TestCase

from history import conf
from history.utils import create_history_table, drop_history_table, get_history_model

from .models import Author, Book


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


class ModelTests (TestCase):

    def setUp(self):
        call_command('triggers')

    def tearDown(self):
        call_command('triggers', drop=True, clear=True)

    def test_history_model(self):
        # Go through the lifecycle of an object - create, update, and delete.
        create_history_table(42)
        author = Author.objects.create(name='Dan Watson')
        pk = author.pk
        author.name = 'Somebody Else'
        author.save()
        author.delete()
        drop_history_table()
        # Get a dyanmic history model we can use with the Django ORM.
        AuthorHistory = get_history_model(Author)
        insert = AuthorHistory.objects.get(transaction_type='+')
        self.assertIsNone(insert.old_value)
        self.assertEqual(insert.new_value, {'id': pk, 'name': 'Dan Watson'})
        self.assertEqual(insert.pk, pk)
        self.assertEqual(insert.user_id, 42)
        update = AuthorHistory.objects.get(transaction_type='~')
        self.assertEqual(update.old_value, insert.new_value)
        self.assertEqual(update.new_value, {'id': pk, 'name': 'Somebody Else'})
        self.assertEqual(update.pk, pk)
        self.assertEqual(update.user_id, 42)
        delete = AuthorHistory.objects.get(transaction_type='-')
        self.assertEqual(delete.old_value, update.new_value)
        self.assertIsNone(delete.new_value)
        self.assertEqual(delete.pk, pk)
        self.assertEqual(delete.user_id, 42)
