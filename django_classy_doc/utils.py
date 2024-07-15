import builtins
from collections import OrderedDict, defaultdict
from copy import copy
import inspect
import pydoc
import sys

from django.conf import settings
from django.db.models import Model
from django.forms.models import ModelForm
from django.forms.forms import BaseForm
from django.utils.module_loading import import_string
from django.utils.html import escape

from . import settings as app_settings


if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec


class DefaultOrderedDict(OrderedDict):

    def __init__(self, default_factory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_factory = default_factory

    def __missing__(self, key):
        value = self.default_factory()
        self[key] = value
        return value


def get_attrs(obj):
    all_attrs = filter(lambda data: pydoc.visiblename(data[0], obj=obj),
                    pydoc.classify_class_attrs(obj))
    return filter(lambda data: data[2] == obj, all_attrs)


def tf_attributes(attr):
    return {
        'name': attr[0],
        'type': attr[1],
        'object': escape(getattr(attr[2], attr[0])),
        'defining_class': attr[2]
    }


def tf_methods(attr):
    arguments = None
    lines = []
    start_line = 0
    source = None

    try:
        func = getattr(attr[2], attr[0])
        docstring = pydoc.getdoc(attr[3])

        # Get the attr arguments
        try:
            args, varargs, keywords, defaults = inspect.getargspec(func)
            arguments = inspect.formatargspec(args, varargs=varargs, varkw=keywords, defaults=defaults)
        except TypeError:
            pass
        except ValueError:
            # ToDo: use inspect.signature() instead of inspect.getargspec()
            pass

        # Get source line details
        try:
            lines, start_line = inspect.getsourcelines(func)
            source = inspect.getsourcefile(func)
        except TypeError:
            pass

    except AttributeError as e:
        docstring = f'{e}'

    return {
        'name': attr[0],
        'type': attr[1],
        'docstring': docstring,
        'defining_class': attr[2],
        'arguments': arguments,
        'code': ''.join(lines),
        'lines': {'start': start_line, 'total': len(lines)},
        'file': source
    }


def tf_everything(attr):
    return {
        'name': attr[0],
        'type': attr[1],
        'rest': attr
    }


def tf_fields(attr):
    field_class = attr[3].__class__
    related = None

    if field_class.__name__.endswith('Descriptor'):
        try:
            field_class = attr[3].field.__class__
            related_model = attr[3].field.remote_field.model
            related = (related_model.__module__, related_model.__name__)
        except Exception:
            pass
    elif field_class.__name__.endswith('DeferredAttribute'):
        try:
            # Related field
            field_class = attr[3].field.remote_field.field.__class__
        except AttributeError:
            # Not a relationship
            field_class = attr[3].field.__class__

    return {
        'name': attr[0],
        'type': attr[1],
        'defining_class': (attr[2].__module__, attr[2].__name__),
        'field_type': field_class.__name__,
        'related': related,
    }


def classify(klass, obj, name=None, mod=None, *ignored):
    if not inspect.isclass(obj):
        raise Exception

    mro = list(reversed(inspect.getmro(obj)))

    klass.update({
        'name': obj.__name__,
        'module': obj.__module__,
        'docstring': pydoc.getdoc(obj),
        'ancestors': [(k.__module__, k.__name__) for k in mro],
        'parents': inspect.getclasstree([obj])[-1][0][1]
    })

    for cls in mro:
        if cls is builtins.object:
            continue

        for attribute in get_attrs(cls):

            if attribute[0] == 'Meta':
                continue

            if attribute[1] == 'data':
                target = 'attributes'
            elif (
                attribute[1] in ['method', 'class method', 'static method'] or attribute[1].endswith('property')
            ) and getattr(attribute[3], '__class__', type).__name__ != "DeferredAttribute":
                target = 'methods'
            elif attribute[1] == 'data descriptor' \
                    or getattr(attribute[3], '__class__', type).__name__ == "DeferredAttribute":
                if attribute[3].__class__.__name__ == 'ReverseOneToOneDescriptor' and attribute[2].__name__ == 'Page':
                    continue
                target = 'fields'
            else:
                target = 'everything'

            tf = globals()[f'tf_{target}']
            tf_ed = tf(attribute)
            name = tf_ed.pop('name')
            klass[target][name].append(tf_ed)

        if issubclass(cls, BaseForm) and hasattr(cls, 'declared_fields'):
            for field, field_type in cls.declared_fields.items():
                klass['fields'][field].append({
                    'name': field,
                    'field_type': field_type.__class__.__name__,
                    'defining_class': (cls.__module__, cls.__name__)
                })

    if issubclass(obj, Model):
        klass['Meta'] = obj._meta.original_attrs
    elif issubclass(obj, ModelForm):
        klass['Meta'] = {
            attr: str(getattr(obj.Meta, attr))
            for attr in dir(obj.Meta)
            if not attr.startswith('__')
        }
    if issubclass(cls, BaseForm) and hasattr(cls, 'base_fields'):
        for field, field_type in cls.base_fields.items():
            if field in klass['fields']:
                continue
            klass['fields'][field].append({
                'name': field,
                'field_type': field_type.__class__.__name__,
                'defining_class': ('Auto', '')
            })

    return klass


def build(thing):
    """Build a dictionary mapping of a class."""
    sys.path.insert(0, '')

    klass = {
        'attributes': DefaultOrderedDict(list),
        'methods': DefaultOrderedDict(list),
        'fields': DefaultOrderedDict(list),
        'properties': [],
        'ancestors': [],
        'parents': [],
        'everything': DefaultOrderedDict(list),
    }

    obj, name = pydoc.resolve(thing, forceload=0)

    if not any(
        [obj.__module__.startswith(base) for base in app_settings.CLASSY_DOC_BASES]
    ) and f'{obj.__module__}.{obj.__name__}' not in app_settings.CLASSY_DOC_ALSO_INCLUDE:
        return False

    return classify(klass, obj, name)


def build_context(klass, exit=True):
    is_documented = False
    if klass in app_settings.CLASSY_DOC_ALSO_INCLUDE:
        is_documented = True
    elif klass not in app_settings.CLASSY_DOC_ALSO_EXCLUDE:
        if not any([
            klass.startswith(app)
            for app in settings.INSTALLED_APPS + app_settings.CLASSY_DOC_NON_INSTALLED_APPS
        ]):
            return False
        if not any([klass.startswith(base) for base in app_settings.CLASSY_DOC_BASES]):
            return False
        if not any([f'.{mod_name}.' in klass for mod_name in app_settings.CLASSY_DOC_MODULE_TYPES]):
            return False
        is_documented = True
    if not is_documented:
        return False

    try:
        structure = build(klass)
        if structure is False:
            return False

    except ImportError as e:
        sys.stderr.write(f'Could not import: {klass}\n')
        if exit:
            sys.exit(1)
        raise e

    for name, lst in structure['attributes'].items():
        for i, definition in enumerate(lst):
            a = definition['defining_class']
            structure['attributes'][name][i]['defining_class'] = (a.__module__, a.__name__)

            if isinstance(definition['object'], list):
                try:
                    s = '[{0}]'.format(', '.join([c.__name__ for c in definition['object']]))
                except AttributeError:
                    pass
                else:
                    structure['attributes'][name][i]['default'] = s
                    continue

    sorted_attributes = sorted(structure['attributes'].items(), key=lambda t: t[0])
    structure['attributes'] = OrderedDict(sorted_attributes)

    sorted_methods = sorted(structure['methods'].items(), key=lambda t: t[0])
    structure['methods'] = OrderedDict(sorted_methods)

    return structure


def build_list_of_documentables(apps=None):
    if apps is None:
        apps = defaultdict(lambda: defaultdict(list))
    klasses = copy(app_settings.CLASSY_DOC_ALSO_INCLUDE)

    for app in list(settings.INSTALLED_APPS) + list(app_settings.CLASSY_DOC_NON_INSTALLED_APPS):
        if not any([app.startswith(base) for base in app_settings.CLASSY_DOC_BASES]):
            continue

        for mod_name in app_settings.CLASSY_DOC_MODULE_TYPES:
            mod_string = f'{app}.{mod_name}'
            print(f'Trying {mod_string}')
            found = False
            for mods in app_settings.CLASSY_DOC_KNOWN_APPS.values():
                if any([f'{mod_string}.'.startswith(f'{mod}.') for mod in mods]):
                    found = True
                    break
            if found:
                continue

            try:
                module = import_string(mod_string)
                for name, obj in inspect.getmembers(module):
                    if not inspect.isclass(obj) or not obj.__module__.startswith(f'{app}.{mod_name}'):
                        continue

                    full_name = f'{app}.{mod_name}.{name}'

                    if full_name in app_settings.CLASSY_DOC_ALSO_EXCLUDE:
                        continue

                    klasses.append(full_name)
                    apps[app][mod_name].append((name, full_name))
            except ImportError as e:
                print(f'Unable to import {app}.{mod_name}', e)

    return apps, klasses


def get_index_context(apps):
    return {
        'apps': {
            app: {
                mod: klasses
                for mod, klasses in modules.items()
            }
            for app, modules in apps.items()
        },
    }
