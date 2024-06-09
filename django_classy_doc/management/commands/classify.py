import builtins
import collections
import inspect
import os
import pydoc
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.html import escape
from django.utils.module_loading import import_string
from django.template.loader import render_to_string

from ...utils import DefaultOrderedDict
from ... import settings as app_settings


if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec


def serve(port, output):
    from http import server
    import socketserver
    import webbrowser

    Handler = server.SimpleHTTPRequestHandler
    port = int(port)
    found_free_port = False
    while not found_free_port:
        try:
            httpd = socketserver.TCPServer(('', port), Handler)
            found_free_port = True
        except OSError:
            port += 1
    print('Serving on port: {0}'.format(port))
    webbrowser.open_new_tab(f'http://localhost:{port}/{output}/classify.html')
    httpd.serve_forever()


def gen_index(apps, output):
    index = render_to_string('django_classy_doc/index.html', {
        'apps': {
            app: {
                mod: klasses
                for mod, klasses in modules.items()
            }
            for app, modules in apps.items()
        },
    })
    with open(output, 'w') as f:
        f.write(index)


def output_path(output, filename='classify.html'):
    path = os.path.join(settings.BASE_DIR, output)
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, filename)


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

            tf = locals()[f'tf_{target}']
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


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('klass', metavar='KLASS', nargs='*')
        parser.add_argument('--output', '-o', action='store', dest='output',
                            default='output', help='Relative path for output files to be saved')
        parser.add_argument('-p', '--port', action='store', dest='port', type=int, default=8000)
        parser.add_argument('-s', '--serve', action='store_true', dest='serve')

    def handle(self, *args, **options):

        klasses = options['klass']
        apps = collections.defaultdict(lambda: collections.defaultdict(list))

        if len(klasses) == 0:
            klasses.extend(app_settings.CLASSY_DOC_ALSO_INCLUDE)

            for app in list(settings.INSTALLED_APPS) + list(app_settings.CLASSY_DOC_NON_INSTALLED_APPS):
                if not any([app.startswith(base) for base in app_settings.CLASSY_DOC_BASES]):
                    continue

                for mod_name in app_settings.CLASSY_DOC_MODULE_TYPES:
                    mod_string = f'{app}.{mod_name}'
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

        for klass in klasses:
            try:
                structure = build(klass)
                if structure is False:
                    continue

            except ImportError:
                sys.stderr.write('Could not import: {0}\n'.format(sys.argv[1]))
                sys.exit(1)

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
            structure['attributes'] = collections.OrderedDict(sorted_attributes)

            sorted_methods = sorted(structure['methods'].items(), key=lambda t: t[0])
            structure['methods'] = collections.OrderedDict(sorted_methods)

            output = render_to_string('django_classy_doc/klass.html', {
                'klass': structure,
                'known_apps': app_settings.CLASSY_DOC_KNOWN_APPS,
            })

            filename = 'classify.html'
            if len(klasses) > 1:
                filename = f'{klass}.html'

            with open(output_path(options['output'], filename), 'w') as f:
                f.write(output)

        if len(klasses) > 1:
            gen_index(apps, output_path(options['output']))

        if options['serve']:
            serve(options['port'], options['output'])
