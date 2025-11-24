# Django Classy DOC

*django-classy-doc* brings [Classy Class-Based Views](https://ccbv.co.uk)-style docs to your own code

## Installation

### From PyPI

```bash
pip install django-classy-doc
```

### From the repo

```bash
pip install -e https://gitlab.levitnet.be/levit/django-classy-doc.git
```

## Getting started

First add `'django_classy_doc',` to your `INSTALLED_APPS` in your `settings.py` file.

To generate the documentation statically, run

```bash
./manage.py classify
```

This will create documentation for your project and save the output in `./output`

For more usage information run

```bash
./manage.py classify --help
```

If instead (or alongside) of generating the documentation statically, 
you can also have Django render the documentation by adding the following line 
to your `urlpatterns` in `urls.py`

```python
urlpatterns = [
  ...
  path('__doc__/', include('django_classy_doc.urls')),
]
```

## Configuration

Set these in your `settings.py` file.

*django-classy-doc* has several configuration options, the most important are `CLASSY_DOC_BASES`, `CLASSY_DOC_MODULE_TYPES` and `CLASSY_DOC_KNOWN_APPS`.

### `CLASSY_DOC_BASES`

This is the list of strings of the base modules you want to document, if you leave it unset, *django-classy-doc* will document every application from your `INSTALLED_APPS`

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


### `CLASSY_DOC_NON_INSTALLED_APPS`

A list of modules, not present in `INSTALLED_APPS` to include in the search for modules. This is mostly useful if you want to document DJango itself.

# Recipes

## CCBV

In order to replicate [CCBV](https://ccbv.co.uk), these are the settings you should set:

```python
CLASSY_DOC_BASES = ['django.views.generic']
CLASSY_DOC_NON_INSTALLED_APPS = ['django.views.generic']
CLASSY_DOC_MODULE_TYPES = [
    'base',
    'dates',
    'detail',
    'edit',
    'list',
]
CLASSY_DOC_KNOWN_APPS = {}
```

If you'd like to include `django.contrib.views` in your documentation, 
you'll first have to include them in your `urls.py`:

```python
urlpatterns = [
  ...
  path('accounts/', include('django.contrib.auth.urls')),
  ...
]
```

Once this is done, you can then use the following settings:

```python
CLASSY_DOC_BASES = ['django.views.generic', 'django.contrib.auth']
CLASSY_DOC_NON_INSTALLED_APPS = ['django.views.generic']
CLASSY_DOC_MODULE_TYPES = [
    'base',
    'dates',
    'detail',
    'edit',
    'list',
    'views',
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

## CDDB

In order to replicate [CDDB](https://cddb.levit.be), these are the settings you should set:

```python
CLASSY_DOC_BASES = ['django.db', 'django.db.models']
CLASSY_DOC_NON_INSTALLED_APPS = ['django.db.models', 'django.db']
CLASSY_DOC_MODULE_TYPES = [
    'base',
    'fields',
    'enums',
    'expressions',
    'constraints',
    'indexes',
    'lookups',
    'aggregates',
    'constants',
    'deletion',
    'functions',
    'manager',
    'query_utils',
    'sql',
    'options',
    'query',
    'signals',
    'utils',
    'transaction',
]
CLASSY_DOC_KNOWN_APPS = {}
```


## CDF

In order to replicate [CDF](https://cdf.9vo.lt), these are the settings you should set:

```python
CLASSY_DOC_BASES = ['django.forms']
CLASSY_DOC_NON_INSTALLED_APPS = ['django.forms']
CLASSY_DOC_MODULE_TYPES = [
    'boundfield',
    'fields',
    'forms',
    'formsets',
    'models',
    'renderers',
    'widgets',
]
CLASSY_DOC_KNOWN_APPS = {}
```

# MkDocs Integration

## mkdocstrings Handler

*django-classy-doc* provides a custom handler for [mkdocstrings](https://mkdocstrings.github.io/) that allows you to embed class documentation directly in your MkDocs-based documentation.

### Installation

Install with the mkdocs extra:

```bash
pip install django-classy-doc[mkdocs]
```

### Configuration

In your `mkdocs.yml`, configure the handler:

```yaml
plugins:
  - mkdocstrings:
      handlers:
        classydoc:
          # Handler options (all optional)
          options:
            show_source: true
            show_mro: true
            show_attributes: true
            show_methods: true
            show_fields: true
            heading_level: 2
```

Make sure to set your `DJANGO_SETTINGS_MODULE` environment variable so the handler can access your Django configuration:

```bash
export DJANGO_SETTINGS_MODULE=myproject.settings
```

### Usage

In your markdown files, use the `::: classydoc` directive to include class documentation:

```markdown
# My Model Documentation

::: myapp.models.MyModel
    handler: classydoc
    options:
      show_source: true
      show_mro: true
```

The handler supports these options:

| Option | Default | Description |
|--------|---------|-------------|
| `show_source` | `true` | Display source code for methods |
| `show_mro` | `true` | Display Method Resolution Order |
| `show_attributes` | `true` | Display class attributes |
| `show_methods` | `true` | Display methods with signatures |
| `show_fields` | `true` | Display Django model fields |
| `heading_level` | `2` | Starting heading level for sections |

## Markdown Formatter

For programmatic use, *django-classy-doc* provides a `MarkdownFormatter` class that generates mkdocs-compatible markdown from classified class data.

### Usage

```python
from django_classy_doc.utils import build
from django_classy_doc.formatters.markdown import MarkdownFormatter

# Get class data
klass_data = build('myapp.models.MyModel')

# Format as markdown
formatter = MarkdownFormatter(klass_data)
markdown_content = formatter.format()
```

The formatter supports Google-style docstrings and will parse sections like Args, Returns, Examples, and Notes into properly formatted markdown.

