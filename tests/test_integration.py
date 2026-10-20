import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('integration', ROOT / 'scripts/integrate_performance.py')
integration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integration)


class IntegrationTests(unittest.TestCase):
    def test_start_and_reload_are_protected_before_proxy_actions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / 'openclash'
            path.write_text('start_service()\n{\n   if procd_running "openclash" >/dev/null; then\ntrue\nfi\n}\n'
                            'stop_service()\n{\nrevert_firewall\n}\nreload_service()\n{\nget_config\n}\n')
            integration.patch_openclash(path)
            text = path.read_text()
            self.assertLess(text.index('arthur-performance protect'), text.index('if procd_running'))
            self.assertIn('return 1;', text)
            self.assertEqual(text.count('arthur-performance protect'), 3)

    def test_changed_openclash_hooks_fail_build_instead_of_silently_skipping_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / 'openclash'
            path.write_text('start_service() { start_proxy; }')
            with self.assertRaises(ValueError): integration.patch_openclash(path)

    def test_feeds_stay_at_tested_revisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / 'feeds.conf.default'
            path.write_text('src-git nss_packages https://example.test/nss.git;main\n')
            integration.pin_feeds(path, {'nss_packages': 'a' * 40})
            self.assertIn('nss.git^' + 'a' * 40, path.read_text())
            self.assertNotIn(';main', path.read_text())

    def test_proxy_keeps_a_package_dependency_on_its_protection_helper(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / 'Makefile'
            path.write_text('define Package/proxy\n DEPENDS:=+curl +bash\nendef\n')
            integration.require_guard_package(path)
            self.assertIn('DEPENDS:=+luci-app-arthur +curl +bash', path.read_text())

    def test_view_urls_change_per_firmware_but_source_file_remains_inspectable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            menu = root / 'package/usr/share/luci/menu.d/luci-app-arthur.json'
            menu.parent.mkdir(parents=True)
            menu.write_text(json.dumps({'test': {'action': {'type': 'view', 'path': 'arthur/network'}}}))
            view = root / 'package/www/luci-static/resources/view/arthur/network.js'
            view.parent.mkdir(parents=True)
            view.write_text('callDiagnose()')
            integration.version_views(root / 'package', root / 'files', 'abc123')
            self.assertEqual(json.loads(menu.read_text())['test']['action']['path'], 'arthur/network-abc123')
            self.assertEqual(view.with_name('network-abc123.js').read_text(), view.read_text())
            self.assertEqual((root / 'files/etc/arthur-build').read_text(), 'abc123\n')
