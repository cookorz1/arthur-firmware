"""Exercise NSS/OpenClash transitions and memory actions on fake kernel nodes."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from test_runtime import UCI_MOCK

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'package/arthur/files/usr/libexec/arthur-performance'
COMMAND = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
base = pathlib.Path(os.environ['MOCK_PERF_BASE'])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (base / 'events').open('a') as stream: stream.write(json.dumps([name, *args]) + '\n')
if name == 'pidof':
    mapping = json.loads((base / 'pids.json').read_text())
    found = sorted(set(str(mapping[key]) for key in args if key in mapping))
    if found: print(' '.join(found))
    sys.exit(0 if found else 1)
if name == 'modprobe' and args[0] == 'ecm':
    if (base / 'load-fails').exists(): sys.exit(1)
    (base / 'modules/ecm').mkdir(exist_ok=True)
    ecm = base / 'ecm'
    (ecm / 'ecm_db').mkdir(parents=True, exist_ok=True)
    for key in ('front_end_ipv4_stop', 'front_end_ipv6_stop'):
        if not (ecm / key).exists(): (ecm / key).write_text('0\n')
    (ecm / 'ecm_db/defunct_all').write_text('0\n')
if name == 'rmmod': sys.exit(1)  # prove the guard fails closed if both pause and unload fail
if name == 'nft':
    if 'flowtable' in args: sys.exit(0 if (base / 'flowtable').exists() else 1)
    sys.exit(0 if (base / 'fw4').exists() else 1)
if name == 'firewall':
    if (base / 'reload-fails').exists(): sys.exit(1)
    (base / 'flowtable').unlink(missing_ok=True)
if name == 'zram':
    marker = base / 'zram-enabled'
    if args[0] == 'enabled': sys.exit(0 if marker.exists() else 1)
    if args[0] == 'enable': marker.touch()
    if args[0] == 'disable': marker.unlink(missing_ok=True)
if name == 'sync' and (base / 'sync-fails').exists(): sys.exit(1)
'''


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = pathlib.Path(self.temporary.name)
        self.proc = self.base / 'proc'
        self.ecm = self.base / 'ecm'
        self.modules = self.base / 'modules'
        self.state = self.base / 'state'
        self.bin = self.base / 'bin'
        self.init = self.base / 'init'
        for path in (self.bin, self.modules, self.init): path.mkdir()
        self.put('proc/sys/net/ipv4/tcp_available_congestion_control', 'cubic reno bbr\n')
        self.put('proc/sys/net/ipv4/tcp_congestion_control', 'cubic\n')
        self.put('proc/sys/net/core/default_qdisc', 'fq_codel\n')
        self.put('proc/sys/vm/drop_caches', '0\n')
        self.put('proc/net/nf_conntrack', 'KEEP ESTABLISHED CONNECTIONS\n')
        self.put('proc/meminfo', 'MemTotal: 416000 kB\nMemAvailable: 160000 kB\nMemFree: 80000 kB\n'
                 'Cached: 65000 kB\nBuffers: 5000 kB\nSReclaimable: 10000 kB\nShmem: 2000 kB\n'
                 'SwapTotal: 131072 kB\nSwapFree: 120000 kB\n')
        self.put('proc/swaps', 'Filename Type Size Used Priority\n/dev/zram0 partition 131072 11072 100\n')
        self.put('pids.json', '{}')
        self.put('build', 'test-build\n')
        self.uci_file = self.base / 'uci.json'
        self.uci_file.write_text(json.dumps({
            'arthur.performance.tcp_cc': 'bbr', 'arthur.performance.nss_mode': 'auto',
            'arthur.performance.zram_enabled': '1', 'openclash.config.enable': '0',
            'network.globals.packet_steering': '0',
            'firewall.@defaults[0].flow_offloading': '0',
            'firewall.@defaults[0].flow_offloading_hw': '0'}))
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        MOCK_UCI=str(self.uci_file), MOCK_PERF_BASE=str(self.base),
                        ARTHUR_PROC_ROOT=str(self.proc), ARTHUR_ECM_ROOT=str(self.ecm),
                        ARTHUR_MODULE_ROOT=str(self.modules), ARTHUR_PERF_STATE=str(self.state),
                        ARTHUR_INIT_ROOT=str(self.init), ARTHUR_BUILD_FILE=str(self.base / 'build'))
        self.command(self.bin / 'uci', UCI_MOCK)
        for name in ('pidof', 'modprobe', 'rmmod', 'nft', 'sync'):
            self.command(self.bin / name, COMMAND)
        for name in ('zram', 'firewall'):
            self.command(self.init / name, COMMAND)

    def put(self, relative, contents):
        path = self.base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)

    def command(self, path, contents):
        path.write_text(contents)
        path.chmod(0o755)

    def update(self, values):
        data = json.loads(self.uci_file.read_text())
        data.update(values)
        self.uci_file.write_text(json.dumps(data))

    def run_action(self, action, success=True):
        result = subprocess.run(['sh', str(SCRIPT), action], env=self.env,
                                capture_output=True, text=True, timeout=15)
        if success: self.assertEqual(result.returncode, 0, result.stderr)
        else: self.assertNotEqual(result.returncode, 0)
        return result.stdout

    def loaded_ecm(self, value=0):
        (self.modules / 'ecm').mkdir(exist_ok=True)
        self.put('ecm/front_end_ipv4_stop', str(value) + '\n')
        self.put('ecm/front_end_ipv6_stop', str(value) + '\n')
        self.put('ecm/ecm_db/defunct_all', '0\n')

    def assert_paused(self):
        self.assertEqual((self.ecm / 'front_end_ipv4_stop').read_text().strip(), '1')
        self.assertEqual((self.ecm / 'front_end_ipv6_stop').read_text().strip(), '1')
        self.assertEqual((self.proc / 'net/nf_conntrack').read_text(), 'KEEP ESTABLISHED CONNECTIONS\n')

    def test_proxy_armed_before_process_starts_pauses_and_drains_nss(self):
        self.loaded_ecm()
        self.update({'openclash.config.enable': '1'})
        self.run_action('reconcile')
        self.assert_paused()
        self.assertEqual((self.ecm / 'ecm_db/defunct_all').read_text().strip(), '1')
        self.assertEqual((self.proc / 'sys/net/ipv4/tcp_congestion_control').read_text().strip(), 'bbr')

    def test_running_proxy_still_blocks_when_config_is_disabled(self):
        self.loaded_ecm()
        self.put('pids.json', '{"clash": 123}')
        self.put('proc/123/status', 'VmRSS: 64000 kB\n')
        self.run_action('reconcile')
        self.assert_paused()
        status = json.loads(self.run_action('status'))
        self.assertTrue(status['proxy_guard'])
        self.assertEqual(status['proxy_rss_kib'], 64000)

    def test_proxy_on_does_not_load_missing_ecm_module(self):
        self.update({'openclash.config.enable': '1'})
        self.run_action('reconcile')
        self.assertFalse((self.modules / 'ecm').exists())

    def test_proxy_off_restores_allowed_acceleration_without_restarting_wifi(self):
        self.loaded_ecm(1)
        (self.modules / 'ath11k').mkdir()
        self.run_action('reconcile')
        self.assertEqual((self.ecm / 'front_end_ipv4_stop').read_text().strip(), '0')
        self.assertTrue((self.modules / 'ath11k').is_dir())
        self.assertNotIn('rmmod', (self.base / 'events').read_text())

    def test_nss_loads_only_when_eligible_and_preserves_existing_connections(self):
        self.run_action('reconcile')
        self.assertTrue((self.modules / 'ecm').exists())
        self.assertEqual((self.ecm / 'front_end_ipv6_stop').read_text().strip(), '0')
        self.assertEqual((self.proc / 'net/nf_conntrack').read_text(), 'KEEP ESTABLISHED CONNECTIONS\n')

    def test_sqm_and_packet_steering_do_not_stack_with_nss(self):
        self.loaded_ecm()
        for values, reason in [({'sqm.test.enabled': '1'}, 'qos'),
                               ({'sqm.test.enabled': '0', 'network.globals.packet_steering': '1'}, 'steering')]:
            self.update(values)
            self.run_action('reconcile')
            self.assert_paused()
            self.assertEqual(json.loads(self.run_action('status'))['reason'], reason)

    def test_explicit_off_is_not_overridden(self):
        self.loaded_ecm()
        self.update({'arthur.performance.nss_mode': 'off'})
        self.run_action('reconcile')
        self.assert_paused()

    def test_protect_fails_closed_when_ecm_cannot_be_stopped(self):
        self.loaded_ecm()
        (self.ecm / 'front_end_ipv4_stop').unlink()
        self.run_action('protect', success=False)
        self.assertEqual((self.state / 'error').read_text().strip(), 'nss_controls_missing')

    def test_stale_acceleration_rules_must_be_drained_before_proxy_start(self):
        self.loaded_ecm(1)
        self.run_action('protect')
        self.assert_paused()
        self.assertEqual((self.ecm / 'ecm_db/defunct_all').read_text().strip(), '1')

    def test_flowtables_disabled_before_proxy_with_reload_only_if_needed(self):
        self.loaded_ecm()
        self.put('fw4', 'active')
        self.put('flowtable', 'active')
        self.update({'firewall.@defaults[0].flow_offloading': '1'})
        self.run_action('protect')
        self.assertFalse((self.base / 'flowtable').exists())
        self.assertEqual(json.loads(self.uci_file.read_text())['firewall.@defaults[0].flow_offloading'], '0')
        self.assert_paused()

    def test_failed_drain_is_retried_and_not_reported_as_a_complete_pause(self):
        self.loaded_ecm()
        self.update({'openclash.config.enable': '1'})
        node = self.ecm / 'ecm_db/defunct_all'
        node.unlink()
        node.mkdir()
        self.run_action('reconcile', success=False)
        self.run_action('reconcile', success=False)
        self.assertFalse((self.state / 'drained').exists())
        self.assertEqual((self.state / 'error').read_text().strip(), 'nss_drain_failed')

    def test_flowtable_reload_failure_keeps_nss_paused_and_reports_error(self):
        self.loaded_ecm()
        self.put('flowtable', 'active')
        self.put('reload-fails', 'yes')
        self.run_action('protect', success=False)
        self.assert_paused()
        self.assertEqual((self.state / 'error').read_text().strip(), 'flowtable_conflict')

    def test_tcp_switch_can_return_to_cubic_and_never_replaces_active_qdiscs(self):
        self.update({'arthur.performance.tcp_cc': 'cubic'})
        self.run_action('reconcile')
        self.assertEqual((self.proc / 'sys/net/ipv4/tcp_congestion_control').read_text().strip(), 'cubic')
        self.assertEqual((self.proc / 'sys/net/core/default_qdisc').read_text().strip(), 'fq')
        self.assertNotIn('"tc"', (self.base / 'events').read_text())

    def test_unavailable_tcp_algorithm_does_not_claim_success_or_overwrite_current(self):
        self.put('proc/sys/net/ipv4/tcp_available_congestion_control', 'cubic reno\n')
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['tcp_cc'], 'cubic')
        self.assertEqual((self.state / 'error').read_text().strip(), 'tcp_algorithm_unavailable')

    def test_zram_disable_is_deferred_and_never_swaps_off_running_memory(self):
        self.put('zram-enabled', '')
        self.update({'arthur.performance.zram_enabled': '0'})
        before = (self.proc / 'swaps').read_text()
        self.run_action('reconcile')
        self.assertFalse((self.base / 'zram-enabled').exists())
        self.assertEqual((self.proc / 'swaps').read_text(), before)
        events = (self.base / 'events').read_text()
        self.assertNotIn('swapoff', events)
        self.assertNotIn('["zram", "stop"]', events)

    def test_read_status_never_loads_nss_or_changes_sysctls(self):
        status = json.loads(self.run_action('status'))
        self.assertFalse((self.modules / 'ecm').exists())
        self.assertEqual((self.proc / 'sys/net/ipv4/tcp_congestion_control').read_text().strip(), 'cubic')
        self.assertEqual(status['memory']['available_kib'], 160000)
        self.assertTrue(status['zram_active'])
        self.assertEqual(status['build'], 'test-build')

    def test_manual_cache_release_preserves_processes_swap_and_connections(self):
        self.put('pids.json', '{"clash": 123}')
        before_swap = (self.proc / 'swaps').read_text()
        result = json.loads(self.run_action('release_memory'))
        self.assertTrue(result['ok'])
        self.assertEqual((self.proc / 'sys/vm/drop_caches').read_text().strip(), '3')
        self.assertEqual((self.proc / 'swaps').read_text(), before_swap)
        self.assertEqual((self.base / 'pids.json').read_text(), '{"clash": 123}')
        self.assertEqual((self.proc / 'net/nf_conntrack').read_text(), 'KEEP ESTABLISHED CONNECTIONS\n')
        self.assertEqual(json.loads(self.run_action('release_memory'))['reason'], 'cooldown')

    def test_sync_failure_cancels_cache_drop(self):
        self.put('sync-fails', 'yes')
        result = json.loads(self.run_action('release_memory'))
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'sync_failed')
        self.assertEqual((self.proc / 'sys/vm/drop_caches').read_text().strip(), '0')

    def test_missing_available_memory_field_uses_reclaimable_memory_fallback(self):
        text = (self.proc / 'meminfo').read_text().replace('MemAvailable: 160000 kB\n', '')
        self.put('proc/meminfo', text)
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['memory']['available_kib'], 158000)
