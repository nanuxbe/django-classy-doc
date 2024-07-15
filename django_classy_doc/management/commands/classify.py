import collections
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from ...utils import build_context, build_list_of_documentables, get_index_context
from ... import settings as app_settings


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
    index = render_to_string('django_classy_doc/index.html', get_index_context(apps))
    with open(output, 'w') as f:
        f.write(index)


def output_path(output, filename='classify.html'):
    path = os.path.join(settings.BASE_DIR, output)
    if not os.path.exists(path):
        os.makedirs(path)
    return os.path.join(path, filename)


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
            klasses = build_list_of_documentables(apps)

        for klass in klasses:
            structure = build_context(klass)
            if structure is False:
                continue

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
