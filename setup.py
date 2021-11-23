import os
import re

from setuptools import find_packages, setup

with open(os.path.join("history", "__init__.py"), "r") as src:
    version = re.match(r'.*__version__ = "(.*?)"', src.read(), re.S).group(1)

setup(
    name="django-history-triggers",
    version=version,
    description="Management command and middleware for Django history triggers.",
    author="Dan Watson",
    author_email="watsond@imsweb.com",
    url="https://github.com/imsweb/django-history-triggers",
    license="BSD",
    packages=find_packages(exclude=("testapp",)),
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Utilities",
    ],
)
