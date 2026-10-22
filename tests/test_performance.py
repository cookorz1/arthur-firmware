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
import json, os, pathlib, shutil, sys
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
if name == 'modprobe' and args[0] in ('nf_flow_table_inet', 'nft_flow_offload'):
    if (base / 'software-module-fails').exists(): sys.exit(1)
if name == 'rmmod':
    if not (base / 'unload-allowed').exists(): sys.exit(1)
    shutil.rmtree(base / 'modules/ecm')
    shutil.rmtree(base / 'ecm')
if name == 'nft':
    if 'flowtable' in args:
        node = base / 'flowtable'
        if not node.exists(): sys.exit(1)
        print('flowtable ft { hook ingress priority filter; devices = { eth0, lan1 };' +
              (' flags offload;' if node.read_text() == 'hardware' else '') + ' }')
        sys.exit(0)
    sys.exit(0 if (base / 'fw4').exists() else 1)
if name == 'firewall':
    if (base / 'reload-fails').exists(): sys.exit(1)
    once = base / 'reload-fails-once'
    if once.exists(): once.unlink(); sys.exit(1)
    cfg_path = pathlib.Path(os.environ['MOCK_UCI'])
    cfg = json.loads(cfg_path.read_text())
    if cfg.get('firewall.@defaults[0].flow_offloading') == '1':
        (base / 'flowtable').write_text('software')
    else: (base / 'flowtable').unlink(missing_ok=True)
    if (base / 'proxy-on-reload').exists():
        cfg['openclash.config.enable'] = '1'
        cfg_path.write_text(json.dumps(cfg))
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
        self.put('proc/stat', 'cpu 0 0 0 0\ncpu0 0 0 0 0\ncpu1 0 0 0 0\ncpu2 0 0 0 0\ncpu3 0 0 0 0\n')
        self.net = self.base / 'net'
        self.net.mkdir()
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
                        ARTHUR_INIT_ROOT=str(self.init), ARTHUR_BUILD_FILE=str(self.base / 'build'),
                        ARTHUR_SYSFS_ROOT=str(self.net),
                        ARTHUR_RPS_HELPER=str(SCRIPT.with_name('arthur-usb-rps')))
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

    def usb_device(self, name='eth0', driver='cdc_ether', index='8', queues=1, initial='0'):
        interface = self.net / name
        interface.mkdir(exist_ok=True)
        self.put('usb/' + name + '/idVendor', '19d2\n')
        device = self.base / 'usb' / name / 'interface'
        device.mkdir(exist_ok=True)
        driver_dir = self.base / 'drivers' / driver
        driver_dir.mkdir(parents=True, exist_ok=True)
        (device / 'driver').symlink_to(driver_dir, target_is_directory=True)
        (interface / 'device').symlink_to(device, target_is_directory=True)
        (interface / 'ifindex').write_text(index + '\n')
        for number in range(queues):
            node = interface / 'queues' / f'rx-{number}' / 'rps_cpus'
            node.parent.mkdir(parents=True)
            node.write_text(initial + '\n')
        return interface / 'queues/rx-0/rps_cpus'

    def test_usb_rps_defaults_on_and_follows_configured_device_not_name_eth0(self):
        first = self.usb_device('usb0', queues=2)
        other = self.usb_device('eth0', index='9')
        self.update({'network.f50.device': 'usb0'})
        self.software_mode()
        self.run_action('reconcile')
        self.assertEqual(first.read_text().strip(), 'b')
        self.assertEqual(first.parent.with_name('rx-1').joinpath('rps_cpus').read_text().strip(), 'b')
        self.assertEqual(other.read_text().strip(), '0')
        rps = json.loads(self.run_action('status'))['usb_rps']
        self.assertTrue(rps['enabled'])
        self.assertEqual(rps['state'], 'active')
        self.assertEqual(rps['device'], 'usb0')

    def test_usb_rps_remains_active_across_proxy_start_reload_and_stop(self):
        node = self.usb_device()
        self.software_mode()
        self.run_action('reconcile')
        self.update({'openclash.config.enable': '1'})
        self.run_action('protect')
        self.run_action('reconcile')
        status = json.loads(self.run_action('status'))
        self.assertTrue(status['proxy_guard'])
        self.assertFalse(status['software_flowtable'])
        self.assertEqual(status['usb_rps']['state'], 'active')
        self.assertEqual(node.read_text().strip(), 'b')
        self.run_action('protect')
        self.put('pids.json', '{"mihomo": 9}')
        self.update({'openclash.config.enable': '0'})
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), 'b')
        self.assertFalse((self.base / 'flowtable').exists())
        self.put('pids.json', '{}')
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'software')
        self.assertEqual(node.read_text().strip(), 'b')

    def test_usb_rps_off_restores_original_setting_and_preserves_explicit_off(self):
        node = self.usb_device(initial='4')
        self.software_mode()
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), 'b')
        self.update({'arthur.performance.usb_rps': '0'})
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '4')
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '4')
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'off')

    def test_usb_rps_does_not_overwrite_later_administrator_changes_on_disable(self):
        node = self.usb_device()
        self.software_mode()
        self.run_action('reconcile')
        node.write_text('3\n')
        self.update({'arthur.performance.usb_rps': '0'})
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '3')

    def test_usb_rps_hot_unplug_and_name_reuse_never_restore_old_device_baseline(self):
        import shutil
        node = self.usb_device()
        self.software_mode()
        self.run_action('reconcile')
        shutil.rmtree(self.net / 'eth0')
        shutil.rmtree(self.base / 'usb/eth0')
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'waiting')
        node = self.usb_device(index='10', initial='2')
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), 'b')
        self.update({'arthur.performance.usb_rps': '0'})
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '2')

    def test_usb_rps_new_device_ifindex_is_detected_without_an_intermediate_watch_cycle(self):
        node = self.usb_device()
        self.software_mode()
        self.run_action('reconcile')
        (self.net / 'eth0/ifindex').write_text('11\n')
        node.write_text('1\n')
        self.run_action('reconcile')
        self.update({'arthur.performance.usb_rps': '0'})
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '1')

    def test_usb_rps_waits_for_device_then_recovers_after_boot(self):
        self.software_mode()
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'waiting')
        node = self.usb_device()
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), 'b')

    def test_usb_rps_survives_qos_protection_without_enabling_flow_bypass(self):
        node = self.usb_device()
        self.software_mode()
        self.update({'sqm.test.enabled': '1'})
        self.run_action('reconcile')
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['reason'], 'qos')
        self.assertFalse(status['software_flowtable'])
        self.assertEqual(node.read_text().strip(), 'b')

    def test_usb_rps_yields_to_nss_but_works_when_proxy_pauses_nss(self):
        node = self.usb_device()
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '0')
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'nss')
        self.update({'openclash.config.enable': '1'})
        self.run_action('protect')
        self.assertEqual(node.read_text().strip(), 'b')
        self.run_action('reconcile')
        self.assert_paused()
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'active')

    def test_usb_rps_yields_to_global_steering_without_fighting_its_values(self):
        node = self.usb_device(initial='2')
        self.software_mode()
        self.run_action('reconcile')
        self.update({'network.globals.packet_steering': '1'})
        node.write_text('f\n')
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), 'f')
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'global_steering')

    def test_usb_rps_offline_cpu_is_excluded_from_b_mask(self):
        node = self.usb_device()
        self.put('proc/stat', 'cpu 0 0 0 0\ncpu0 0 0 0 0\ncpu1 0 0 0 0\n')
        self.software_mode()
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '3')

    def test_usb_rps_partial_apply_failure_restores_other_queues(self):
        node = self.usb_device(queues=2)
        second = node.parent.with_name('rx-1') / 'rps_cpus'
        second.write_text('invalid-mask\n')
        self.software_mode()
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '0')
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['usb_rps']['state'], 'error')
        self.assertEqual(status['usb_rps']['error'], 'apply_failed')
        self.assertEqual(status['active_backend'], 'software')

    def test_switching_back_to_nss_restores_our_usb_steering(self):
        node = self.usb_device(initial='2')
        self.software_mode()
        self.run_action('reconcile')
        self.update({'arthur.performance.nss_mode': 'auto'})
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '2')
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['active_backend'], 'nss')
        self.assertEqual(status['usb_rps']['state'], 'nss')

    def test_usb_rps_rejects_non_tether_and_raw_modem_drivers(self):
        node = self.usb_device(driver='qmi_wwan')
        self.software_mode()
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '0')
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'waiting')

    def test_usb_rps_status_reports_live_masks_without_writing_them(self):
        node = self.usb_device()
        self.software_mode()
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['usb_rps']['state'], 'pending')
        self.assertEqual(status['usb_rps']['queues'][0]['mask'], '0')
        self.assertEqual(node.read_text().strip(), '0')
        self.assertFalse((self.state / 'usb-rps').exists())

    def test_usb_disabled_restores_rps_without_changing_proxy_or_firewall_policy(self):
        node = self.usb_device()
        self.software_mode()
        self.run_action('reconcile')
        self.update({'arthur.usb.enabled': '0'})
        self.run_action('reconcile')
        self.assertEqual(node.read_text().strip(), '0')
        self.assertEqual(json.loads(self.run_action('status'))['usb_rps']['state'], 'usb_disabled')

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

    def software_mode(self):
        self.update({'arthur.performance.nss_mode': 'software'})
        self.put('fw4', 'active')
        self.put('unload-allowed', 'yes')

    def test_software_mode_unloads_ecm_then_enables_only_software_flowtable(self):
        self.loaded_ecm()
        (self.modules / 'ath11k').mkdir()
        self.software_mode()
        self.run_action('reconcile')
        self.assertFalse((self.modules / 'ecm').exists())
        self.assertTrue((self.modules / 'ath11k').exists())
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['active_backend'], 'software')
        self.assertEqual(status['mode'], 'software')
        self.assertTrue(status['software_flowtable'])
        cfg = json.loads(self.uci_file.read_text())
        self.assertEqual(cfg['firewall.@defaults[0].flow_offloading_hw'], '0')
        events = [json.loads(line) for line in (self.base / 'events').read_text().splitlines()]
        self.assertLess(events.index(['rmmod', 'ecm']), events.index(['firewall', 'reload']))
        self.assertEqual((self.proc / 'net/nf_conntrack').read_text(), 'KEEP ESTABLISHED CONNECTIONS\n')

    def test_steady_software_mode_does_not_reload_firewall_every_watch_cycle(self):
        self.software_mode()
        self.run_action('reconcile')
        before = (self.base / 'events').read_text().count('["firewall", "reload"]')
        self.run_action('reconcile')
        self.assertEqual((self.base / 'events').read_text().count('["firewall", "reload"]'), before)
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'software')

    def test_switch_to_nss_removes_flowtable_before_loading_ecm(self):
        self.software_mode()
        self.run_action('reconcile')
        self.update({'arthur.performance.nss_mode': 'auto'})
        (self.base / 'events').write_text('')
        self.run_action('reconcile')
        events = [json.loads(line) for line in (self.base / 'events').read_text().splitlines()]
        self.assertLess(events.index(['firewall', 'reload']), events.index(['modprobe', 'ecm', 'front_end_selection=1']))
        self.assertFalse((self.base / 'flowtable').exists())
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'nss')

    def test_software_mode_suspends_for_proxy_then_resumes_selected_mode(self):
        self.software_mode()
        self.run_action('reconcile')
        self.update({'openclash.config.enable': '1'})
        self.run_action('reconcile')
        status = json.loads(self.run_action('status'))
        self.assertTrue(status['proxy_guard'])
        self.assertFalse(status['software_flowtable'])
        self.assertEqual(status['active_backend'], 'off')
        self.assertEqual(status['mode'], 'software')
        self.update({'openclash.config.enable': '0'})
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'software')

    def test_running_proxy_and_qos_both_block_software_mode(self):
        self.software_mode()
        self.run_action('reconcile')
        self.put('pids.json', '{"mihomo": 9}')
        self.run_action('reconcile')
        self.assertFalse((self.base / 'flowtable').exists())
        self.put('pids.json', '{}')
        self.update({'sqm.test.enabled': '1'})
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['reason'], 'qos')
        self.assertFalse((self.base / 'flowtable').exists())

    def test_protect_removes_software_rules_before_core_start(self):
        self.software_mode()
        self.run_action('reconcile')
        self.run_action('protect')
        self.assertFalse((self.base / 'flowtable').exists())
        self.assertEqual(json.loads(self.uci_file.read_text())['firewall.@defaults[0].flow_offloading'], '0')

    def test_protect_still_removes_flowtable_when_ecm_pause_and_unload_fail(self):
        self.loaded_ecm()
        (self.ecm / 'front_end_ipv4_stop').unlink()
        self.put('fw4', 'active')
        self.put('flowtable', 'active')
        self.update({'firewall.@defaults[0].flow_offloading': '1'})
        self.run_action('protect', success=False)
        self.assertFalse((self.base / 'flowtable').exists())
        self.assertEqual(json.loads(self.run_action('status'))['error'], 'nss_controls_missing')

    def test_failed_software_protection_reports_conflict_instead_of_success(self):
        self.software_mode()
        self.run_action('reconcile')
        self.put('reload-fails', 'yes')
        self.update({'openclash.config.enable': '1'})
        self.run_action('protect', success=False)
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['active_backend'], 'conflict')
        self.assertEqual(status['error'], 'flowtable_conflict')

    def test_packet_steering_is_not_a_nss_conflict_in_software_mode(self):
        self.software_mode()
        self.update({'network.globals.packet_steering': '1'})
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'software')

    def test_software_mode_fails_closed_when_ecm_will_not_unload(self):
        self.loaded_ecm()
        self.software_mode()
        (self.base / 'unload-allowed').unlink()
        self.run_action('reconcile', success=False)
        self.assert_paused()
        self.assertFalse((self.base / 'flowtable').exists())
        self.assertEqual(json.loads(self.run_action('status'))['error'], 'nss_unload_failed')

    def test_missing_software_module_does_not_leave_offload_enabled(self):
        self.software_mode()
        self.put('software-module-fails', 'yes')
        self.run_action('reconcile', success=False)
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['error'], 'software_module_unavailable')
        self.assertEqual(status['active_backend'], 'off')
        self.assertFalse((self.base / 'flowtable').exists())

    def test_software_apply_failure_rolls_back_to_unaccelerated_forwarding(self):
        self.software_mode()
        self.put('reload-fails-once', 'yes')
        self.run_action('reconcile', success=False)
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['error'], 'software_apply_failed')
        self.assertFalse(status['software_flowtable'])
        self.assertEqual(json.loads(self.uci_file.read_text())['firewall.@defaults[0].flow_offloading'], '0')

    def test_proxy_armed_during_software_enable_is_checked_again(self):
        self.software_mode()
        self.put('proxy-on-reload', 'yes')
        self.run_action('reconcile')
        status = json.loads(self.run_action('status'))
        self.assertTrue(status['proxy_guard'])
        self.assertFalse(status['software_flowtable'])
        self.assertEqual(status['active_backend'], 'off')

    def test_software_mode_does_not_mistake_hardware_rules_for_software_rules(self):
        self.software_mode()
        self.update({'firewall.@defaults[0].flow_offloading': '1'})
        self.put('flowtable', 'hardware')
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'conflict')
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'software')
        self.assertEqual((self.base / 'flowtable').read_text(), 'software')

    def test_early_boot_waits_for_firewall_without_claiming_acceleration(self):
        self.software_mode()
        (self.base / 'fw4').unlink()
        self.run_action('reconcile')
        status = json.loads(self.run_action('status'))
        self.assertEqual(status['error'], '')
        self.assertEqual(status['active_backend'], 'off')
        self.put('fw4', 'active')
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'software')

    def test_explicit_off_clears_software_rules_and_status_stays_read_only(self):
        self.software_mode()
        self.run_action('reconcile')
        self.update({'arthur.performance.nss_mode': 'off'})
        # Reading a changed selection reports the conflict, never silently repairs it.
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'conflict')
        self.assertTrue((self.base / 'flowtable').exists())
        self.run_action('reconcile')
        self.assertEqual(json.loads(self.run_action('status'))['active_backend'], 'off')
        self.assertFalse((self.base / 'flowtable').exists())

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
