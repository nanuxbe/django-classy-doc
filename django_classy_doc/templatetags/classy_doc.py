from django import template
from django.conf import settings
from django.utils.text import capfirst

from django_classy_doc import settings as app_settings

register = template.Library()


@register.filter
def class_from(value, arg):
    from_map = app_settings.CLASSY_DOC_KNOWN_APPS

    try:
        return any([value['defining_class'].__module__.startswith(f'{mod}.') for mod in from_map.get(arg, [])])
    except AttributeError:
        # it's a tuple not a string
        return any([value['defining_class'][0].startswith(f'{mod}') for mod in from_map.get(arg, [])])
    except Exception:
        return False


@register.filter
def display_if(value):
    from_map = app_settings.CLASSY_DOC_KNOWN_APPS

    try:
        module_name = value['defining_class'].__module__
    except AttributeError:
        # it's a tuple not a string
        module_name = value['defining_class'][0]

    for name, mods in from_map.items():
        if any([module_name.startswith(f'{mod}.') or module_name == mod for mod in mods]):
            return f'show{capfirst(name)}'

    return 'true'


@register.simple_tag
def init_show_vars():
    from_map = app_settings.CLASSY_DOC_KNOWN_APPS

    return ', '.join([f'show{capfirst(app)}: false' for app in from_map.keys()])


@register.filter
def module(value):
    return value['defining_class'].__module__


@register.filter
def class_name(value):
    return value['defining_class'].__name__


@register.filter
def field_items(value):
    return value['fields'].items()
