"""Tests for the resource reference parser."""
import unittest

from mcp_client_for_ollama.resources.parser import (
    extract_resource_refs,
    extract_template_variables,
    resolve_template,
    ResourceRef,
)


class TestExtractResourceRefs(unittest.TestCase):
    """Tests for extract_resource_refs()."""
    # Helpers
    def _refs(self, text, known=()):
        _, refs = extract_resource_refs(text, set(known))
        return refs

    def _clean(self, text, known=()):
        clean, _ = extract_resource_refs(text, set(known))
        return clean
    # Basic URI detection (scheme-based)
    def test_single_uri_at_start(self):
        refs = self._refs('@file:///readme.md')
        self.assertEqual(refs, [ResourceRef('file:///readme.md', False)])

    def test_clean_text_empty_when_only_uri(self):
        clean = self._clean('@file:///readme.md')
        self.assertEqual(clean, '')

    def test_inline_uri_amid_text(self):
        clean, refs = extract_resource_refs('tell me about @file:///readme.md please', set())
        self.assertEqual(refs, [ResourceRef('file:///readme.md', False)])
        self.assertEqual(clean, 'tell me about please')

    def test_multiple_inline_uris(self):
        clean, refs = extract_resource_refs(
            '@file:///a.txt @file:///b.txt compare these', set()
        )
        self.assertEqual(len(refs), 2)
        self.assertIn(ResourceRef('file:///a.txt', False), refs)
        self.assertIn(ResourceRef('file:///b.txt', False), refs)
        self.assertEqual(clean, 'compare these')

    def test_uri_at_end_of_sentence(self):
        clean, refs = extract_resource_refs('summarise @file:///notes.md', set())
        self.assertEqual(refs, [ResourceRef('file:///notes.md', False)])
        self.assertEqual(clean, 'summarise')

    def test_various_schemes(self):
        for scheme in ('http://', 'https://', 'db://', 'custom://'):
            with self.subTest(scheme=scheme):
                uri = f'{scheme}example'
                refs = self._refs(f'@{uri}')
                self.assertEqual(refs, [ResourceRef(uri, False)])
    # Disambiguation: emails and plain @-words must NOT be extracted
    def test_email_address_not_extracted(self):
        clean, refs = extract_resource_refs('email me at user@example.com', set())
        self.assertEqual(refs, [])
        self.assertEqual(clean, 'email me at user@example.com')

    def test_plain_at_word_not_extracted(self):
        clean, refs = extract_resource_refs('hello @world today', set())
        self.assertEqual(refs, [])
        self.assertEqual(clean, 'hello @world today')

    def test_at_without_scheme_not_extracted_unless_known(self):
        clean, refs = extract_resource_refs('@username something', set())
        self.assertEqual(refs, [])
        self.assertEqual(clean, '@username something')
    # known_uris: non-scheme URIs that are explicitly registered
    def test_known_uri_without_scheme_extracted(self):
        known = {'custom:resource'}
        refs = self._refs('@custom:resource', known)
        self.assertEqual(refs, [ResourceRef('custom:resource', False)])

    def test_unknown_uri_without_scheme_not_extracted(self):
        refs = self._refs('@custom:resource', known=())
        self.assertEqual(refs, [])
    # Template detection
    def test_template_uri_detected(self):
        refs = self._refs('@file:///{path}')
        self.assertEqual(refs, [ResourceRef('file:///{path}', True)])

    def test_multi_variable_template(self):
        refs = self._refs('@db://{host}/{db}')
        self.assertEqual(refs, [ResourceRef('db://{host}/{db}', True)])

    def test_non_template_uri_is_template_false(self):
        refs = self._refs('@file:///readme.md')
        self.assertFalse(refs[0].is_template)
    # Trailing punctuation stripping
    def test_trailing_period_stripped(self):
        refs = self._refs('see @file:///readme.md.')
        self.assertEqual(refs, [ResourceRef('file:///readme.md', False)])

    def test_trailing_comma_stripped(self):
        refs = self._refs('see @file:///readme.md,')
        self.assertEqual(refs, [ResourceRef('file:///readme.md', False)])

    def test_trailing_paren_stripped(self):
        refs = self._refs('read (@file:///readme.md)')
        self.assertEqual(refs, [ResourceRef('file:///readme.md', False)])
    # Edge cases
    def test_empty_input(self):
        clean, refs = extract_resource_refs('', set())
        self.assertEqual(refs, [])
        self.assertEqual(clean, '')

    def test_only_plain_text(self):
        clean, refs = extract_resource_refs('just a regular query', set())
        self.assertEqual(refs, [])
        self.assertEqual(clean, 'just a regular query')

    def test_duplicate_uri_extracted_twice(self):
        refs = self._refs('@file:///a.txt @file:///a.txt diff')
        self.assertEqual(len(refs), 2)

    def test_whitespace_normalized_in_clean_text(self):
        clean = self._clean('a @file:///b.txt  c')
        self.assertEqual(clean, 'a c')

    def test_mid_sentence_resource_ref(self):
        """@uri in middle or end of sentence should be extracted."""
        clean, refs = extract_resource_refs(
            'summarize the key features from @server://info', set()
        )
        self.assertEqual(refs, [ResourceRef('server://info', False)])
        self.assertEqual(clean, 'summarize the key features from')


class TestExtractTemplateVariables(unittest.TestCase):
    """Tests for extract_template_variables()."""

    def test_single_variable(self):
        self.assertEqual(extract_template_variables('file:///{path}'), ['path'])

    def test_multiple_variables(self):
        self.assertEqual(
            extract_template_variables('db://{host}/{db}/table/{id}'),
            ['host', 'db', 'id'],
        )

    def test_no_variables(self):
        self.assertEqual(extract_template_variables('file:///readme.md'), [])

    def test_empty_string(self):
        self.assertEqual(extract_template_variables(''), [])

    def test_adjacent_variables(self):
        self.assertEqual(extract_template_variables('{a}{b}'), ['a', 'b'])


class TestResolveTemplate(unittest.TestCase):
    """Tests for resolve_template()."""

    def test_single_variable(self):
        result = resolve_template('file:///{path}', {'path': 'src/main.py'})
        self.assertEqual(result, 'file:///src/main.py')

    def test_multiple_variables(self):
        result = resolve_template('db://{host}/{db}', {'host': 'localhost', 'db': 'mydb'})
        self.assertEqual(result, 'db://localhost/mydb')

    def test_missing_variable_unchanged(self):
        result = resolve_template('file:///{path}', {})
        self.assertEqual(result, 'file:///{path}')

    def test_extra_variable_in_dict_ignored(self):
        result = resolve_template('file:///{path}', {'path': 'a.txt', 'extra': 'nope'})
        self.assertEqual(result, 'file:///a.txt')

    def test_empty_template(self):
        result = resolve_template('', {'x': 'y'})
        self.assertEqual(result, '')

    def test_no_variables_in_template(self):
        result = resolve_template('file:///readme.md', {'path': 'ignored'})
        self.assertEqual(result, 'file:///readme.md')


if __name__ == '__main__':
    unittest.main()
