from django.core.management import call_command
from django.test import TestCase

from history import backends, get_history_model

from .models import Author

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
        with self.backend.session(username="nobody"):
            dan = Author.objects.create(name="Dan Watson")
            alexa = Author.objects.create(name="Alexa Watson")
        self.assertEqual(HistoryModel.objects.count(), 2)
        self.assertEqual(dan.history.count(), 1)
        self.assertEqual(alexa.history.count(), 1)
        h1 = dan.history.get()
        h2 = alexa.history.get()
        self.assertEqual(h1.session_id, h2.session_id)
        self.assertEqual(h1.session_date, h2.session_date)
        self.assertEqual(h1.get_user(), h2.get_user())
        self.assertEqual(h1.get_user(), "nobody")

    def test_extra(self):
        with self.backend.session(username="somebody", extra="special"):
            author = Author.objects.create(name="Dan Watson")
        h1 = author.history.get()
        self.assertEqual(h1.get_user(), "somebody")
        self.assertEqual(h1.extra, "special")


class MiddlewareTests(TriggersTestCase):
    def test_lifecycle(self):
        self.client.get("/lifecycle/")
        self.assertEqual(HistoryModel.objects.count(), 1)
        insert = HistoryModel.objects.get()
        self.assertEqual(insert.get_user(), "webuser")
