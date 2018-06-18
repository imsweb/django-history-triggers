from setuptools import find_packages, setup

import history


setup(
    name='django-history-triggers',
    version=history.__version__,
    description='Management command and middleware for Django history triggers.',
    author='Dan Watson',
    author_email='watsond@imsweb.com',
    url='https://github.com/imsweb/django-history-triggers',
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ]
)
