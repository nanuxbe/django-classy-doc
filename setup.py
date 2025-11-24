import os
from setuptools import setup, find_namespace_packages

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django_classy_doc',
    version='0.0.9',
    packages=find_namespace_packages(include=[
        'django_classy_doc',
        'django_classy_doc.*',
        'mkdocstrings_handlers.*',
    ]),
    include_package_data=True,
    license='MIT License',  # example license
    description='Django package to generate ccbv.co.uk-style documentation for your own code',
    long_description=README,
    long_description_content_type="text/markdown",
    url='https://github.com/nanuxbe/django-classy-doc',
    author='LevIT SCS',
    author_email='info@levit.be',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 5.0',
        'Framework :: Django :: 4.2',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',  # example license
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        'Django>=3.2',
    ],
    extras_require={
        'mkdocs': [
            'mkdocstrings>=0.20',
            'mkdocs>=1.5',
        ],
    },
    entry_points={
        'mkdocstrings.handlers': [
            'classydoc = mkdocstrings_handlers.classydoc:get_handler',
        ],
    },
    package_data={
        'mkdocstrings_handlers.classydoc': [
            'templates/material/*.jinja',
            'templates/material/*.css',
        ],
    },
)

