import binascii
import os
import uuid

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.utils import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from history import backends, get_history_model
from history.models import TriggerType
from history.templatetags.history import json_format

from .models import Author, Book, CustomHistory, RandomData


def nofilter(model, field, trigger):
    return True


def replace(d, **kwargs):
    new_dict = d.copy()
    new_dict.update(kwargs)
    return new_dict


def test_request_context(request):
    return {"username": "webuser"}


class TriggersTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        call_command("triggers", "--quiet", "enable")

    @classmethod
    def tearDownClass(cls):
        call_command("triggers", "--clear", "--quiet", "disable")
        super().tearDownClass()

    def setUp(self):
        self.backend = backends.get_backend(cache=False)


@override_settings(
    HISTORY_MODEL="custom.CustomHistory",
    HISTORY_REQUEST_CONTEXT=test_request_context,
)
class BasicTests(TriggersTestCase):
    def test_backend_cache(self):
        b1 = backends.get_backend()
        b2 = backends.get_backend()
        self.assertIs(b1, b2)

    def test_basics(self):
        with self.backend.session(username="nobody") as session:
            a = Author.objects.create(name="Nobody")
            pk = a.pk
            a.name = "Somebody"
            a.picture = os.urandom(128)
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
        self.assertEqual(insert.snapshot, {"id": pk, "name": "Nobody"})
        self.assertIsNone(insert.changes)
        # Check update history.
        self.assertEqual(update.session_id, session.session_id)
        self.assertEqual(update.get_user(), "nobody")
        self.assertEqual(update.snapshot, {"id": pk, "name": "Somebody"})
        self.assertEqual(update.changes, {"name": ["Nobody", "Somebody"]})
        # Check delete history.
        self.assertEqual(delete.session_id, session.session_id)
        self.assertEqual(delete.get_user(), "nobody")
        self.assertIsNone(delete.snapshot)
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

    def test_data_types(self):
        data = {"hello": "world", "answer": 42, "cost": 12.99}
        now = timezone.now()
        with self.backend.session(username="data") as session:
            obj = RandomData.objects.create(data=data.copy(), date=now)
            obj.data["answer"] = 420
            obj.ident = uuid.uuid4()
            obj.save()
            obj.delete()
        self.assertEqual(session.history.count(), 3)
        insert = session.history.get(change_type=TriggerType.INSERT)
        update = session.history.get(change_type=TriggerType.UPDATE)
        delete = session.history.get(change_type=TriggerType.DELETE)
        self.assertEqual(insert.snapshot["data"], data)
        self.assertEqual(update.changes["data"][0], data)
        self.assertEqual(update.changes["data"][1], replace(data, answer=420))
        self.assertEqual(uuid.UUID(update.snapshot["ident"]), obj.ident)
        self.assertIsNone(delete.snapshot)
        self.assertIsNone(delete.changes)

    def test_change_pk(self):
        with self.backend.session(username="unholy") as session:
            a = Author.objects.create(name="Bad Idea")
            with self.backend.conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE {table} SET id = {new_pk} WHERE id = {old_pk}".format(
                        table=Author._meta.db_table,
                        new_pk=666,
                        old_pk=a.pk,
                    )
                )
        self.assertEqual(session.history.count(), 2)
        update = session.history.get(change_type=TriggerType.UPDATE)
        self.assertEqual(a.pk, update.object_id)
        self.assertEqual(update.snapshot, {"id": 666, "name": "Bad Idea"})
        self.assertEqual(update.changes, {"id": [a.pk, 666]})

    def test_session_decorator(self):
        @self.backend.session(username="decorator")
        def decorator_test():
            RandomData.objects.create()

        decorator_test()
        h = RandomData.history.get()
        self.assertEqual(h.change_type, TriggerType.INSERT)
        self.assertEqual(h.username, "decorator")


@override_settings(HISTORY_SNAPSHOTS=False)
class NoSnapshotTests(TriggersTestCase):
    def test_no_snapshots(self):
        with self.backend.session() as session:
            a = Author.objects.create(name="Nobody")
            a.name = "Somebody"
            a.picture = os.urandom(128)
            a.save()
            a.delete()
        self.assertEqual(session.history.count(), 3)
        insert = session.history.get(change_type=TriggerType.INSERT)
        update = session.history.get(change_type=TriggerType.UPDATE)
        delete = session.history.get(change_type=TriggerType.DELETE)
        self.assertIsNone(insert.snapshot)
        self.assertIsNone(insert.changes)
        self.assertIsNone(update.snapshot)
        self.assertEqual(update.changes, {"name": ["Nobody", "Somebody"]})
        self.assertIsNone(delete.snapshot)
        self.assertIsNone(delete.changes)


@override_settings(HISTORY_FILTER=nofilter)
class BinaryTests(TriggersTestCase):
    def test_binary_data(self):
        old_data = os.urandom(1024)
        new_data = os.urandom(1024)
        with self.backend.session() as session:
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
        with self.backend.session() as session:
            dan.delete()
        self.assertEqual(session.history.count(), 1)


@override_settings(ROOT_URLCONF="custom.urls", HISTORY_MIDDLEWARE_IGNORE=["/ignore"])
class MiddlewareTests(TriggersTestCase):
    def test_lifecycle(self):
        UserModel = get_user_model()
        HistoryModel = get_history_model()
        with self.backend.session():
            user = UserModel.objects.create_user("testuser")
            self.client.force_login(user)
        self.client.get("/lifecycle/")
        # Insert user, update user (last_login), insert Author.
        self.assertEqual(HistoryModel.objects.count(), 3)
        insert = Author.history.get()
        self.assertEqual(insert.get_user(), user)

    def test_ignore_prefix(self):
        self.client.get("/ignored/")
        self.assertEqual(RandomData.objects.count(), 1)
        self.assertEqual(RandomData.history.count(), 1)
        self.assertIsNone(RandomData.history.get().user)


class TemplateTagTests(TestCase):
    def test_json_format(self):
        self.assertEqual(json_format(None), "")
        self.assertEqual(json_format(42), 42)
        self.assertEqual(
            json_format({"name": "Dan", "address": "123 Main St."}),
            "address = 123 Main St.<br />name = Dan",
        )
