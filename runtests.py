#!/usr/bin/env python
import os
import sys

import django
from django.test.utils import get_runner

if __name__ == "__main__":
    # The "tests" directory is not itself a python module, but is where we want to find
    # the test modules and common settings/urls.
    base_path = os.path.dirname(os.path.abspath(__file__))
    test_path = os.path.join(base_path, "tests")
    sys.path.insert(0, test_path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    from django.conf import settings

    test_modules = ["custom"]
    settings.INSTALLED_APPS += test_modules
    django.setup()

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(test_modules)
    if failures:
        sys.exit(1)
