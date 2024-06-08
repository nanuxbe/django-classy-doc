# Django Classy DOC

*django-classy-doc* brings [Classy Class-Based Views](https://ccbv.co.uk)-style docs to your own code

## Installation

```bash
pip install -e https://gitlab.levitnet.be/levit/django-classy-doc.git
```

## Getting started

To generate the documentation, run

```bash
./manage.py classify
```

This will create documentation for your project and save the output in `./output`

For more usage information run

```bash
./manage.py classify --help
```

## Configuration

Set these in your `settings.py` file.

*django-classy-doc* has several configuration options, the 2 most important are `CLASSY_DOC_BASES` and `CLASSY_DOC_KNOWN_APPS`.

### `CLASSY_DOC_BASES`

This is the list of strings of the base modules you want to document, if you leave it unset, *djang-classy-doc* will document every application from your `INSTALLED_APPS`

*django-classy-docs* will string-match everything from your `INSTALLED_APPS` that **starts with** any of the mentioned strings

ex:
```python
CLASSY_DOC_BASES = ['catalog', 'custom_auth', 'account']
```

### `CLASSY_DOC_KNOWN_APPS`

A dictionary of lists that represents the "known apps" that you want to hide by default. This means that properties and methods present in your classes (that extend these bases classes) that are only defined in these base classes, will be hidden at first.
All sections of the generated documentation will have a checkbox for each of these known apps that will let you show/hide thes properties and methods

ex:
```python
CLASSY_KNOWN_APPS = {
  'django': ['django'],                                                      
  'DRF': ['rest_framework', 'django_filters'],
  'wagtail': ['wagtail', 'treebeard', 'modelcluster'],
}
```
