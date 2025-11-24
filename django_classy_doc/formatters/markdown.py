"""Markdown formatter for django_classy_doc.

Generates mkdocs-compatible markdown documentation from classified class data.
Supports Google-style docstring parsing.
"""

import html
import re
from collections import OrderedDict


class GoogleDocstringParser:
    """Parser for Google-style docstrings.

    Parses sections like Args, Returns, Examples, Raises, Attributes, Notes.
    """

    SECTION_NAMES = [
        'Args',
        'Arguments',
        'Attributes',
        'Example',
        'Examples',
        'Keyword Args',
        'Keyword Arguments',
        'Note',
        'Notes',
        'Other Parameters',
        'Parameters',
        'Raises',
        'Returns',
        'Return',
        'See Also',
        'Todo',
        'Warning',
        'Warnings',
        'Yields',
    ]

    def __init__(self, docstring):
        """Initialize the parser.

        Args:
            docstring: The raw docstring to parse
        """
        self.docstring = docstring or ''
        self._parsed = None

    def parse(self):
        """Parse the docstring into sections.

        Returns:
            Dict with keys: summary, description, and section names in lowercase
        """
        if self._parsed is not None:
            return self._parsed

        result = {
            'summary': '',
            'description': '',
        }

        if not self.docstring:
            self._parsed = result
            return result

        lines = self.docstring.split('\n')

        # Find summary (first paragraph)
        summary_lines = []
        idx = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped:
                summary_lines.append(stripped)
            else:
                break
        else:
            # Loop completed without break - move past last line
            idx += 1

        result['summary'] = ' '.join(summary_lines)

        # Skip blank lines after summary
        while idx < len(lines) and not lines[idx].strip():
            idx += 1

        # Build section pattern
        section_pattern = re.compile(
            r'^(' + '|'.join(re.escape(s) for s in self.SECTION_NAMES) + r'):\s*$'
        )

        # Find all section starts
        current_section = 'description'
        section_content = []

        for i in range(idx, len(lines)):
            line = lines[i]
            match = section_pattern.match(line.strip())

            if match:
                # Save previous section
                if section_content:
                    key = current_section.lower().replace(' ', '_')
                    result[key] = self._process_section(current_section, section_content)
                    section_content = []

                current_section = match.group(1)
            else:
                section_content.append(line)

        # Save last section
        if section_content:
            key = current_section.lower().replace(' ', '_')
            result[key] = self._process_section(current_section, section_content)

        self._parsed = result
        return result

    def _process_section(self, section_name, lines):
        """Process a section's content based on section type.

        Args:
            section_name: Name of the section
            lines: List of content lines

        Returns:
            Processed content (string or list of dicts for Args/Attributes)
        """
        # Remove common leading whitespace
        if lines:
            # Find minimum indentation (ignoring empty lines)
            min_indent = float('inf')
            for line in lines:
                if line.strip():
                    leading = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, leading)

            if min_indent == float('inf'):
                min_indent = 0

            lines = [line[min_indent:] if len(line) > min_indent else line.lstrip() for line in lines]

        # For Args/Attributes/Parameters, parse into structured format
        if section_name.lower() in ['args', 'arguments', 'parameters', 'attributes', 'keyword args', 'keyword arguments']:
            return self._parse_params(lines)

        # For Returns/Raises/Yields, keep as text
        return '\n'.join(lines).strip()

    def _parse_params(self, lines):
        """Parse parameter/attribute section into list of dicts.

        Args:
            lines: Content lines of the section

        Returns:
            List of dicts with keys: name, type, description
        """
        params = []
        current_param = None
        desc_lines = []

        # Pattern: name (type): description  OR  name: description
        param_pattern = re.compile(r'^(\w+)(?:\s*\(([^)]+)\))?:\s*(.*)$')

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if current_param and desc_lines:
                    desc_lines.append('')
                continue

            match = param_pattern.match(stripped)

            if match and not line.startswith(' ' * 4):  # New param (not continuation)
                # Save previous param
                if current_param:
                    current_param['description'] = ' '.join(desc_lines).strip()
                    params.append(current_param)
                    desc_lines = []

                current_param = {
                    'name': match.group(1),
                    'type': match.group(2) or '',
                    'description': '',
                }
                if match.group(3):
                    desc_lines = [match.group(3)]
            elif current_param:
                # Continuation of description
                desc_lines.append(stripped)

        # Save last param
        if current_param:
            current_param['description'] = ' '.join(desc_lines).strip()
            params.append(current_param)

        return params


class MarkdownFormatter:
    """Format classified class data as mkdocs-compatible markdown."""

    def __init__(self, klass_data, known_apps=None):
        """Initialize the formatter.

        Args:
            klass_data: Dict from classify() function
            known_apps: Dict mapping app names to module patterns (for filtering)
        """
        self.klass_data = klass_data
        self.known_apps = known_apps or {}

    def format(self):
        """Generate markdown content for the class.

        Returns:
            Markdown string
        """
        lines = []

        # Title
        class_name = self.klass_data.get('name', 'Unknown')
        module = self.klass_data.get('module', '')
        lines.append(f'# {class_name}')
        lines.append('')

        if module:
            lines.append(f'`{module}.{class_name}`')
            lines.append('')

        # Parse and render docstring
        docstring = self.klass_data.get('docstring', '')
        parsed_doc = GoogleDocstringParser(docstring).parse()

        # Summary
        if parsed_doc.get('summary'):
            lines.append(parsed_doc['summary'])
            lines.append('')

        # Description
        if parsed_doc.get('description'):
            lines.append(parsed_doc['description'])
            lines.append('')

        # Class Attributes from docstring
        if parsed_doc.get('attributes'):
            lines.extend(self._format_docstring_attributes(parsed_doc['attributes']))

        # Examples from docstring
        if parsed_doc.get('examples') or parsed_doc.get('example'):
            examples = parsed_doc.get('examples') or parsed_doc.get('example')
            lines.extend(self._format_examples(examples))

        # Notes from docstring
        if parsed_doc.get('notes') or parsed_doc.get('note'):
            notes = parsed_doc.get('notes') or parsed_doc.get('note')
            lines.extend(self._format_notes(notes))

        # Method Resolution Order
        if self.klass_data.get('ancestors'):
            lines.extend(self._format_mro())

        # Attributes (code-level)
        if self.klass_data.get('attributes'):
            lines.extend(self._format_attributes())

        # Methods
        if self.klass_data.get('methods'):
            lines.extend(self._format_methods())

        # Fields (for Django models)
        if self.klass_data.get('fields'):
            lines.extend(self._format_fields())

        return '\n'.join(lines)

    def _format_docstring_attributes(self, attributes):
        """Format attributes from docstring as a table.

        Args:
            attributes: List of attribute dicts from docstring parser

        Returns:
            List of markdown lines
        """
        lines = [
            '## Class Attributes',
            '',
            '| Attribute | Type | Description |',
            '|-----------|------|-------------|',
        ]

        for attr in attributes:
            name = f"`{attr['name']}`"
            type_str = f"`{attr['type']}`" if attr.get('type') else '-'
            desc = attr.get('description', '').replace('|', '\\|').replace('\n', ' ')
            lines.append(f'| {name} | {type_str} | {desc} |')

        lines.append('')
        return lines

    def _format_examples(self, examples):
        """Format examples section.

        Args:
            examples: String containing examples

        Returns:
            List of markdown lines
        """
        lines = [
            '## Examples',
            '',
        ]

        # Process example text - look for code blocks indicated by ::
        example_lines = examples.split('\n')
        in_code_block = False
        code_lines = []

        for line in example_lines:
            stripped = line.strip()

            if stripped.endswith('::'):
                # Start of code block
                if in_code_block and code_lines:
                    lines.append('```python')
                    lines.extend(code_lines)
                    lines.append('```')
                    lines.append('')
                    code_lines = []

                # Add the description without ::
                desc = stripped[:-2].strip()
                if desc:
                    lines.append(f'**{desc}**')
                    lines.append('')
                in_code_block = True

            elif in_code_block:
                if stripped and not line.startswith(' ' * 4) and not line.startswith('\t'):
                    # End of code block
                    if code_lines:
                        lines.append('```python')
                        lines.extend(code_lines)
                        lines.append('```')
                        lines.append('')
                        code_lines = []
                    in_code_block = False
                    lines.append(line)
                else:
                    # Inside code block
                    # Remove leading 4 spaces
                    if line.startswith('    '):
                        code_lines.append(line[4:])
                    elif line.startswith('\t'):
                        code_lines.append(line[1:])
                    elif not stripped:
                        code_lines.append('')
                    else:
                        code_lines.append(line)
            else:
                lines.append(line)

        # Close any remaining code block
        if code_lines:
            lines.append('```python')
            lines.extend(code_lines)
            lines.append('```')
            lines.append('')

        return lines

    def _format_notes(self, notes):
        """Format notes section.

        Args:
            notes: String containing notes

        Returns:
            List of markdown lines
        """
        lines = [
            '## Notes',
            '',
        ]

        for line in notes.split('\n'):
            stripped = line.strip()
            if stripped.startswith('- '):
                lines.append(stripped)
            elif stripped:
                lines.append(stripped)
            else:
                lines.append('')

        lines.append('')
        return lines

    def _format_mro(self):
        """Format Method Resolution Order.

        Returns:
            List of markdown lines
        """
        lines = [
            '## Method Resolution Order',
            '',
        ]

        ancestors = self.klass_data.get('ancestors', [])
        for i, (module, name) in enumerate(ancestors, 1):
            if name == 'object':
                continue
            lines.append(f'{i}. `{module}.{name}`')

        lines.append('')
        return lines

    def _format_attributes(self):
        """Format code-level attributes as a table.

        Returns:
            List of markdown lines
        """
        lines = [
            '## Attributes',
            '',
            '| Attribute | Value | Defined in |',
            '|-----------|-------|------------|',
        ]

        for attr_name, declarations in sorted(self.klass_data['attributes'].items()):
            if not declarations:
                continue

            first_decl = declarations[0] if isinstance(declarations, list) else declarations
            defining_class = self._get_defining_class_str(first_decl)

            value = first_decl.get('object', '') if isinstance(first_decl, dict) else ''
            if first_decl.get('default'):
                value = first_decl['default']

            value_str = self._format_attribute_value(value)
            lines.append(f'| `{attr_name}` | `{value_str}` | {defining_class} |')

        lines.append('')
        return lines

    def _format_methods(self):
        """Format methods with signatures and source code.

        Returns:
            List of markdown lines
        """
        lines = [
            '## Methods',
            '',
        ]

        for method_name, declarations in sorted(self.klass_data['methods'].items()):
            if not declarations:
                continue

            decl_list = declarations if isinstance(declarations, list) else [declarations]
            first_decl = decl_list[0]

            # Get method signature
            arguments = first_decl.get('arguments') if isinstance(first_decl, dict) else None
            if not arguments:
                arguments = '(self)'

            # Get method type
            method_type = first_decl.get('type', 'method')
            type_indicator = ''
            if method_type == 'class method':
                type_indicator = ' `@classmethod`'
            elif method_type == 'static method':
                type_indicator = ' `@staticmethod`'
            elif 'property' in method_type:
                type_indicator = ' `@property`'

            defining_class = self._get_defining_class_str(first_decl)

            lines.append(f'### `{method_name}{arguments}`{type_indicator}')
            lines.append('')

            if defining_class:
                lines.append(f'**Defined in:** {defining_class}')
                lines.append('')

            # Get and parse docstring
            docstring = first_decl.get('docstring', '') if isinstance(first_decl, dict) else ''
            if docstring:
                parsed = GoogleDocstringParser(docstring).parse()

                # Summary
                if parsed.get('summary'):
                    lines.append(parsed['summary'])
                    lines.append('')

                # Description
                if parsed.get('description'):
                    lines.append(parsed['description'])
                    lines.append('')

                # Args
                if parsed.get('args') or parsed.get('arguments') or parsed.get('parameters'):
                    params = parsed.get('args') or parsed.get('arguments') or parsed.get('parameters')
                    lines.append('**Arguments:**')
                    lines.append('')
                    for param in params:
                        type_str = f' ({param["type"]})' if param.get('type') else ''
                        lines.append(f'- **{param["name"]}**{type_str}: {param.get("description", "")}')
                    lines.append('')

                # Returns
                if parsed.get('returns') or parsed.get('return'):
                    returns = parsed.get('returns') or parsed.get('return')
                    lines.append(f'**Returns:** {returns}')
                    lines.append('')

                # Raises
                if parsed.get('raises'):
                    lines.append('**Raises:**')
                    lines.append('')
                    lines.append(parsed['raises'])
                    lines.append('')

            # Show source code (with docstring stripped)
            for decl in decl_list:
                if not isinstance(decl, dict):
                    continue

                code = decl.get('code', '')
                if code:
                    # Strip docstring from source code
                    code = self._strip_docstring_from_code(code)

                    if len(decl_list) > 1:
                        decl_class = self._get_defining_class_str(decl)
                        lines.append(f'**Source from {decl_class}:**')
                        lines.append('')

                    lines.append('```python')
                    lines.append(code.strip())
                    lines.append('```')
                    lines.append('')

        return lines

    def _strip_docstring_from_code(self, code):
        """Strip the docstring from method source code.

        Args:
            code: Source code string

        Returns:
            Code with docstring removed
        """
        # Pattern to match docstring at start of function body
        # Matches: def ...: followed by optional whitespace and triple-quoted string
        pattern = r'^([ \t]*def[^:]+:\s*\n)([ \t]*)(["\'])\3\3(.*?)\3\3\3'

        match = re.search(pattern, code, re.DOTALL)
        if match:
            # Remove the docstring, keeping the def line
            def_line = match.group(1)
            # Find where the docstring ends
            docstring_end = match.end()
            rest_of_code = code[docstring_end:]

            # If only whitespace remains after stripping, add pass
            if not rest_of_code.strip():
                indent = match.group(2)
                return def_line + indent + 'pass'

            return def_line + rest_of_code.lstrip('\n')

        return code

    def _format_fields(self):
        """Format Django model fields.

        Returns:
            List of markdown lines
        """
        lines = [
            '## Fields',
            '',
            '| Field | Type | Related To |',
            '|-------|------|------------|',
        ]

        for field_name, declarations in sorted(self.klass_data['fields'].items()):
            if not declarations:
                continue

            first_decl = declarations[0] if isinstance(declarations, list) else declarations

            field_type = first_decl.get('field_type', '-')
            related = first_decl.get('related')
            if related:
                related_str = f'`{related[0]}.{related[1]}`'
            else:
                related_str = '-'

            lines.append(f'| `{field_name}` | `{field_type}` | {related_str} |')

        lines.append('')
        return lines

    def _get_defining_class_str(self, declaration):
        """Extract defining class string from a declaration dict.

        Args:
            declaration: Dict with 'defining_class' key

        Returns:
            String like 'module.ClassName'
        """
        if not isinstance(declaration, dict):
            return ''

        defining_class = declaration.get('defining_class')
        if not defining_class:
            return ''

        if isinstance(defining_class, tuple):
            return f'{defining_class[0]}.{defining_class[1]}'
        elif hasattr(defining_class, '__module__') and hasattr(defining_class, '__name__'):
            return f'{defining_class.__module__}.{defining_class.__name__}'
        else:
            return str(defining_class)

    def _format_attribute_value(self, value):
        """Format attribute value for markdown display.

        Args:
            value: The attribute value

        Returns:
            Formatted string suitable for markdown table
        """
        if value is None:
            return 'None'

        value_str = str(value)

        # Decode HTML entities
        value_str = html.unescape(value_str)

        # Clean up class representations: <class 'foo.Bar'> → foo.Bar
        class_match = re.match(r"^<class '([^']+)'>$", value_str)
        if class_match:
            value_str = class_match.group(1)

        # Clean up function repr: <function name at 0x...> → name()
        value_str = re.sub(r'<function ([^\s>]+)[^>]*>', r'\1()', value_str)

        # Clean up bound method repr
        value_str = re.sub(r'<bound method ([^>]+)>', r'\1()', value_str)

        # Truncate long values
        if len(value_str) > 50:
            value_str = value_str[:47] + '...'

        # Escape pipe characters and remove newlines for table compatibility
        value_str = value_str.replace('|', '\\|').replace('\n', ' ')

        return value_str


def format_index(klasses, title='API Reference'):
    """Generate index markdown for multiple classes.

    Args:
        klasses: List of klass_data dicts
        title: Title for the index page

    Returns:
        Markdown string
    """
    lines = [
        f'# {title}',
        '',
        'Auto-generated API documentation.',
        '',
        '| Class | Module | Description |',
        '|-------|--------|-------------|',
    ]

    for klass in klasses:
        name = klass.get('name', 'Unknown')
        module = klass.get('module', '')
        docstring = klass.get('docstring', '')

        # Get first line of docstring as description
        desc = docstring.split('\n')[0] if docstring else ''
        if len(desc) > 60:
            desc = desc[:57] + '...'
        desc = desc.replace('|', '\\|')

        # Create link
        filename = f'{name}.md'
        link = f'[{name}]({filename})'

        lines.append(f'| {link} | `{module}` | {desc} |')

    lines.append('')
    return '\n'.join(lines)
