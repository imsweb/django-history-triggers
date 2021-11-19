from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from history import backends
from history.utils import get_history_model

from .models import Author


class TriggersTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        call_command("triggers", "--quiet")
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        call_command("triggers", "--quiet", "drop")
        call_command("triggers", "--quiet", "clear")

    def setUp(self):
        self.backend = backends.get_backend()


class UtilsTests(TriggersTestCase):
    def test_create_drop_history_table(self):
        self.backend.set_user(42)
        self.assertEqual(self.backend.get_user(), 42)
        self.backend.set_user(88)
        self.assertEqual(self.backend.get_user(), 88)
        self.backend.clear_user()
        self.assertEqual(self.backend.get_user(), None)


class ModelTests(TriggersTestCase):
    def test_history_model(self):
        # Go through the lifecycle of an object - create, update, and delete.
        self.backend.set_user(42)
        author = Author.objects.create(name="Dan Watson")
        pk = author.pk
        author.name = "Somebody Else"
        author.save()
        self.assertEqual(author.history.count(), 2)
        author.delete()
        self.backend.clear_user()
        # Get a dyanmic history model we can use with the Django ORM.
        AuthorHistory = get_history_model(Author)
        insert = AuthorHistory.objects.get(event_type="+")
        self.assertIsNone(insert.changes)
        self.assertEqual(insert.snapshot, {"id": pk, "name": "Dan Watson"})
        self.assertEqual(insert.object_id, pk)
        self.assertEqual(insert.user_id, 42)
        with self.assertRaises(User.DoesNotExist):
            insert.user
        update = AuthorHistory.objects.get(event_type="~")
        self.assertEqual(update.changes, {"name": ["Dan Watson", "Somebody Else"]})
        self.assertEqual(update.snapshot, {"id": pk, "name": "Somebody Else"})
        self.assertEqual(update.object_id, pk)
        self.assertEqual(update.user_id, 42)
        delete = AuthorHistory.objects.get(event_type="-")
        self.assertEqual(delete.snapshot, update.snapshot)
        self.assertIsNone(delete.changes)
        self.assertEqual(delete.object_id, pk)
        self.assertEqual(delete.user_id, 42)


class MiddlewareTests(TriggersTestCase):
    def test_lifecycle(self):
        r = self.client.get("/lifecycle/")
        self.assertEqual(r.json(), {})
        AuthorHistory = get_history_model(Author)
        insert = AuthorHistory.objects.get(event_type="+")
        self.assertEqual(insert.user_id, 42)
