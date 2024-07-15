from django.http import Http404
from django.views.generic import TemplateView

from .utils import build_context, build_list_of_documentables, get_index_context
from . import settings as app_settings


class ClassyView(TemplateView):
    template_name = 'django_classy_doc/klass.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        klass = self.kwargs['klass']

        try:
            context['klass'] = build_context(klass, exit=False)
        except ImportError:
            raise Http404(f'Unable to import {klass}')
        if context['klass'] is False:
            raise Http404(f'Undocuemented class {klass}')
        context['known_apps'] = app_settings.CLASSY_DOC_KNOWN_APPS

        return context


class ClassyIndexView(TemplateView):
    template_name = 'django_classy_doc/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        apps, _ = build_list_of_documentables()
        context.update(get_index_context(apps))
        return context
