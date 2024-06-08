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

*django-classy-doc* has several configuration options, the most important are `CLASSY_DOC_BASES`, `CLASSY_DOC_MODULE_TYPES` and `CLASSY_DOC_KNOWN_APPS`.

### `CLASSY_DOC_BASES`

This is the list of strings of the base modules you want to document, if you leave it unset, *djang-classy-doc* will document every application from your `INSTALLED_APPS`

*django-classy-docs* will string-match everything from your `INSTALLED_APPS` that **starts with** any of the mentioned strings

ex:
```python
CLASSY_DOC_BASES = ['catalog', 'custom_auth', 'account']
```

### `CLASSY_DOC_MODULE_TYPES`

These are the modules type *django-classy-doc* will try to import from every application that matches `CLASSY_DOC_BASES`. It defaults to `['models', 'views']`.

So, assuming your project looks like this:
```
+  mod1
|  +  apps.py
|  +  admin.py
|  +  models.py
|  +  views.py
+  mod2
|  +  apps.py
|  +  admin.py
|  +  models.py
+  mod3
|  +  apps.py
|  +  views.py
```

The following modules will be documented: `mod1.models`, `mod1.views`, `mod2.models`, `mod3.views`

### `CLASSY_DOC_KNOWN_APPS`

A dictionary of lists that represents the "known apps" that you want to hide by default. This means that properties and methods present in your classes (that extend these bases classes) that are only defined in these base classes, will be hidden at first.
All sections of the generated documentation will have a checkbox for each of these known apps that will let you show/hide thes properties and methods.

If left unset, it will default to `{'django': ['django']}`

ex:
```python
CLASSY_KNOWN_APPS = {
  'django': ['django'],                                                      
  'DRF': ['rest_framework', 'django_filters'],
  'wagtail': ['wagtail', 'treebeard', 'modelcluster'],
}
```

## Other configuration

### `CLASSY_DOC_ALSO_INCLUDE`

A list of modules (that would otherwise not be matched) that *django-classy-doc* should also try to document. This defaults to an empty list.

### `CLASSY_DOC_ALSO_EXCLUDE`

A list of modules (that would otherwise be matched) that *django-classy-doc* **should not** try to document. This defaults to an empty list.

# Recipes

## CCBV

In order to replicate [CCBV](https://ccbv.co.uk), these are the settings you should set:

```python
CLASSY_DOC_BASES = ['django']
CLASSY_DOC_MODULE_TYPES = [
    'views.generic.base',
    'views.generic.dates',
    'views.generic.detail',
    'views.generic.edit',
    'views.generic.list',
]
CLASSY_DOC_KNOWN_APPS = {}
```

## CDRF

In order to replicate [CDRF](https://cdrf.co), these are the settings you should set:

```python
CLASSY_DOC_BASES = ['rest_framework']
CLASSY_DOC_MODULE_TYPES = ['generics', 'mixins', 'pagination', 'serializers', 'views', 'viewsets']
CLASSY_DOC_KNOWN_APPS = {}
```
