import collections
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from ...utils import build_context, build_list_of_documentables, get_index_context
from ... import settings as app_settings
from ...formatters.markdown import MarkdownFormatter, format_index


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
        parser.add_argument('--clean', action='store_true', dest='clean',
                            help='Clear html files from output directory before generating new files')
        parser.add_argument('--format', '-f', action='store', dest='format',
                            default='html', choices=['html', 'markdown'],
                            help='Output format: html or markdown (default: html)')
        parser.add_argument('--title', action='store', dest='title',
                            default='API Reference',
                            help='Title for the index page (markdown format only)')
        parser.add_argument('--no-index', action='store_true', dest='no_index',
                            help='Skip generating index file')

    def handle(self, *args, **options):
        output_format = options['format']
        file_extension = '.md' if output_format == 'markdown' else '.html'

        if options['clean']:
            output_dir = os.path.join(settings.BASE_DIR, options['output'])
            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    if not filename.endswith(file_extension):
                        continue
                    file_path = os.path.join(output_dir, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)

        klasses = options['klass']
        apps = collections.defaultdict(lambda: collections.defaultdict(list))

        if len(klasses) == 0:
            apps, klasses = build_list_of_documentables(apps)

        # Collect all structures for markdown index
        all_structures = []

        for klass in klasses:
            structure = build_context(klass)
            if structure is False:
                continue

            if output_format == 'markdown':
                # Use markdown formatter
                formatter = MarkdownFormatter(structure, app_settings.CLASSY_DOC_KNOWN_APPS)
                output_content = formatter.format()
                all_structures.append(structure)

                if len(klasses) == 1:
                    filename = 'index.md'
                else:
                    name = structure["name"]
                    # Use kebab-case if configured
                    if getattr(app_settings, 'CLASSY_DOC_KEBAB_CASE_FILENAMES', False):
                        import re
                        # Handle acronyms properly (e.g., CSSAsset -> css-asset, not c-s-s-asset)
                        name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1-\2', name)
                        name = re.sub(r'([a-z\d])([A-Z])', r'\1-\2', name)
                        name = name.lower()
                    filename = f'{name}.md'
            else:
                # Use HTML template
                output_content = render_to_string('django_classy_doc/klass.html', {
                    'klass': structure,
                    'known_apps': app_settings.CLASSY_DOC_KNOWN_APPS,
                })

                filename = 'classify.html'
                if len(klasses) > 1:
                    filename = f'{klass}.html'

            with open(output_path(options['output'], filename), 'w') as f:
                f.write(output_content)

        # Generate index
        if len(klasses) > 1 and not options['no_index']:
            if output_format == 'markdown':
                # Generate markdown index
                index_content = format_index(all_structures, title=options['title'])
                index_filename = 'index.md'
            else:
                # Generate HTML index
                index_content = render_to_string('django_classy_doc/index.html', get_index_context(apps))
                index_filename = 'index.html'

            with open(output_path(options['output'], index_filename), 'w') as f:
                f.write(index_content)

        if options['serve']:
            if output_format == 'markdown':
                self.stdout.write(self.style.WARNING(
                    'Serve option is not supported for markdown format. '
                    'Use mkdocs serve instead.'
                ))
            else:
                serve(options['port'], options['output'])
