import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('theme', ROOT / 'scripts/integrate_theme.py')
theme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(theme)


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = pathlib.Path(self.temp.name)
        self.templates = self.source / 'feeds/luci/themes/luci-theme-argon/ucode/template/themes/argon'
        self.templates.mkdir(parents=True)
        for name in ('header.ut', 'header_login.ut'):
            (self.templates / name).write_text("<head>mode = cfg.get_first('argon', 'global', 'mode');</head>")
        (self.templates / 'footer.ut').write_text("L.require('menu-argon')")
        self.resources = self.source / 'package/custom/arthur/files/www/luci-static/resources'
        self.resources.mkdir(parents=True)
        (self.resources / 'arthur-shell.js').write_text('shell')

    def test_both_headers_and_shell_use_the_same_build_version(self):
        theme.integrate(self.source, ROOT, 'abc123')
        for name in ('header.ut', 'header_login.ut'):
            self.assertIn('theme.css?v=abc123', (self.templates/name).read_text())
            self.assertIn('avatar.jpg?v=abc123', (self.templates/name).read_text())
        style = (self.source/'package/custom/arthur/files/www/luci-static/arthur/theme.css').read_text()
        self.assertIn('avatar.jpg?v=abc123', style)
        self.assertNotIn('@ARTHUR_BUILD@', style)
        self.assertNotIn('url(logo.svg)', style)
        self.assertIn('arthur-shell-abc123', (self.templates/'footer.ut').read_text())
        self.assertEqual((self.resources/'arthur-shell-abc123.js').read_text(), 'shell')

    def test_template_change_fails_instead_of_building_a_partial_skin(self):
        (self.templates/'header.ut').write_text('changed')
        with self.assertRaises(ValueError): theme.integrate(self.source, ROOT, 'abc123')

    def test_login_posts_to_luci_with_original_fields_and_error_state(self):
        theme.integrate(self.source, ROOT, 'abc123')
        text = (self.templates/'sysauth.ut').read_text(encoding='utf-8')
        for token in ('method="post"', "http.getenv('REQUEST_URI')", 'name="luci_username"', 'name="luci_password"', 'if (fuser)', 'entityencode(duser, true)'):
            self.assertIn(token, text)
        self.assertNotIn('value="password"', text)
        self.assertNotIn('@ARTHUR_VERSION@', text)
        self.assertIn((ROOT/'VERSION').read_text().strip(), text)
        self.assertIn('by-cookorz', text)

    def test_untrusted_build_identifier_is_rejected(self):
        with self.assertRaises(ValueError): theme.integrate(self.source, ROOT, '"><script>')

