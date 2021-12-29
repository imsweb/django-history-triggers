import binascii
import os

from django.core.management import call_command
from django.db.utils import IntegrityError
from django.test import TestCase

from history import backends, get_history_model
from history.models import TriggerType

from .models import Author, Book, CustomHistory

HistoryModel = get_history_model()


class TriggersTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        call_command("triggers", "--quiet", "enable")
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        call_command("triggers", "--quiet", "disable")

    def setUp(self):
        self.backend = backends.get_backend()


class BasicTests(TriggersTestCase):
    def test_basics(self):
        with self.backend.session(username="nobody") as session:
            a = Author.objects.create(name="Nobody")
            pk = a.pk
            a.name = "Somebody"
            a.save()
            a.delete()
        self.assertEqual(session.history.count(), 3)
        insert = session.history.get(change_type=TriggerType.INSERT)
        update = session.history.get(change_type=TriggerType.UPDATE)
        delete = session.history.get(change_type=TriggerType.DELETE)
        # Check insert history.
        self.assertIs(insert.__class__, CustomHistory)
        self.assertEqual(insert.session_id, session.session_id)
        self.assertEqual(insert.get_user(), "nobody")
        self.assertEqual(insert.snapshot, {"id": pk, "name": "Nobody", "picture": None})
        self.assertIsNone(insert.changes)
        # Check update history.
        self.assertEqual(update.session_id, session.session_id)
        self.assertEqual(update.get_user(), "nobody")
        self.assertEqual(
            update.snapshot, {"id": pk, "name": "Somebody", "picture": None}
        )
        self.assertEqual(update.changes, {"name": ["Nobody", "Somebody"]})
        # Check delete history.
        self.assertEqual(delete.session_id, session.session_id)
        self.assertEqual(delete.get_user(), "nobody")
        self.assertEqual(
            delete.snapshot, {"id": pk, "name": "Somebody", "picture": None}
        )
        self.assertIsNone(delete.changes)

    def test_no_session(self):
        with self.assertRaises(IntegrityError):
            Author.objects.create(name="Error")

    def test_nested_sessions(self):
        with self.backend.session(username="first") as s1:
            Author.objects.create(name="First")
            with self.backend.session(username="second") as s2:
                Author.objects.create(name="Second")
            Author.objects.create(name="Third")
        self.assertEqual(Author.history.count(), 3)
        self.assertEqual(s1.history.count(), 2)
        self.assertEqual(s2.history.count(), 1)
        for h in s1.history:
            self.assertEqual(h.get_user(), "first")
        for h in s2.history:
            self.assertEqual(h.get_user(), "second")

    def test_binary_data(self):
        old_data = os.urandom(1024)
        new_data = os.urandom(1024)
        with self.backend.session(username="nobody") as session:
            dan = Author.objects.create(name="Dan Watson", picture=old_data)
            dan.picture = new_data
            dan.save()
        self.assertEqual(session.history.count(), 2)
        self.assertEqual(dan.history.count(), 2)
        insert = session.history.get(change_type=TriggerType.INSERT)
        self.assertTrue(insert.snapshot["picture"].startswith("\\x"))
        self.assertEqual(binascii.unhexlify(insert.snapshot["picture"][2:]), old_data)
        update = session.history.get(change_type=TriggerType.UPDATE)
        self.assertTrue(update.snapshot["picture"].startswith("\\x"))
        self.assertEqual(binascii.unhexlify(update.snapshot["picture"][2:]), new_data)
        self.assertIn("picture", update.changes)
        old_hex, new_hex = update.changes["picture"]
        self.assertTrue(old_hex.startswith("\\x"))
        self.assertEqual(binascii.unhexlify(old_hex[2:]), old_data)
        self.assertTrue(new_hex.startswith("\\x"))
        self.assertEqual(binascii.unhexlify(new_hex[2:]), new_data)
        with self.backend.session(username="nobody") as session:
            dan.delete()
        self.assertEqual(session.history.count(), 1)
        delete = session.history.get()
        self.assertTrue(delete.snapshot["picture"].startswith("\\x"))
        self.assertEqual(binascii.unhexlify(delete.snapshot["picture"][2:]), new_data)

    def test_extra(self):
        with self.backend.session(username="somebody", extra="special"):
            author = Author.objects.create(name="Dan Watson")
        h1 = author.history.get()
        self.assertEqual(h1.get_user(), "somebody")
        self.assertEqual(h1.extra, "special")

    def test_reserved_name(self):
        with self.backend.session(username="somebody"):
            book = Book.objects.create(title="Some Book", order=1)
            book.year = 1981
            book.order = 2
            book.save()
        self.assertEqual(book.history.count(), 2)


class MiddlewareTests(TriggersTestCase):
    def test_lifecycle(self):
        self.client.get("/lifecycle/")
        self.assertEqual(HistoryModel.objects.count(), 1)
        insert = HistoryModel.objects.get()
        self.assertEqual(insert.get_user(), "webuser")
