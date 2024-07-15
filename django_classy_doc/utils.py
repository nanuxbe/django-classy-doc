import builtins
from collections import OrderedDict
import inspect
import pydoc
import sys

from django.conf import settings
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
            if attribute[0] == 'Meta' or attribute[0].startswith('__'):
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
