from app.utils.credentials import sanitize_secret


class TestSanitizeSecret:
    def test_strips_whitespace_and_newlines(self):
        assert sanitize_secret('  secret\r\n') == 'secret'
        assert sanitize_secret('\npass\nword\n') == 'password'

    def test_removes_zero_width_and_bom(self):
        raw = '\ufeff\u200bsec\u200cret\u200d'
        assert sanitize_secret(raw) == 'secret'

    def test_preserves_internal_spaces_and_special_chars(self):
        assert sanitize_secret(' p@ss word! ') == 'p@ss word!'
        assert sanitize_secret("ab'c\"d\\e") == "ab'c\"d\\e"

    def test_empty_and_none(self):
        assert sanitize_secret(None) == ''
        assert sanitize_secret('') == ''
        assert sanitize_secret('   ') == ''

    def test_optional_no_strip_whitespace(self):
        assert sanitize_secret('  x  ', strip_whitespace=False) == '  x  '
