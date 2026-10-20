"""Offline behavioral tests for sysfs link reporting and persistent USB control."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'package/arthur/files'
USB = PACKAGE / 'usr/libexec/arthur-usb'
STATUS = PACKAGE / 'usr/libexec/rpcd/arthur'
WIFI = ROOT / 'files/etc/uci-defaults/99-arthur-wireless'

UCI_MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
path = pathlib.Path(os.environ['MOCK_UCI'])
data = json.loads(path.read_text())
args = [arg for arg in sys.argv[1:] if arg != '-q']
command = args.pop(0)
if command == 'get':
    if args[0] not in data: sys.exit(1)
    print(data[args[0]])
elif command == 'show':
    for key, value in data.items():
        if key.startswith(args[0] + '.'):
            print(key + '=' + (value if value in ('wifi-device', 'wifi-iface') else repr(value)))
elif command in ('set', 'add_list'):
    key, value = args[0].split('=', 1)
    data[key] = value if command == 'set' else (data.get(key, '') + ' ' + value).strip()
    path.write_text(json.dumps(data))
elif command == 'commit':
    pass
else:
    raise SystemExit('Unsupported mock UCI command: ' + command)
'''


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = pathlib.Path(self.temporary.name)
        self.net = self.base / 'sys/class/net'
        self.net.mkdir(parents=True)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.uci_file = self.base / 'uci.json'
        self.events = self.base / 'events.txt'
        self.uci_file.write_text(json.dumps({
            'arthur.usb.enabled': '1',
            'firewall.@zone[0]': 'zone',
            'firewall.@zone[0].name': 'wan',
            'firewall.@zone[0].network': 'wan wan6'
        }))
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        ARTHUR_SYSFS_ROOT=str(self.net),
                        ARTHUR_LOCK_DIR=str(self.base / 'usb.lock'),
                        MOCK_UCI=str(self.uci_file), MOCK_EVENTS=str(self.events),
                        MOCK_BASE=str(self.base))
        self.command('uci', UCI_MOCK)
        for name in ('ifup', 'ifdown', 'logger', 'wifi'):
            self.command(name, '#!/bin/sh\nprintf "%s\\n" "' + name + ' $*" >>"$MOCK_EVENTS"\n')
        self.command('ubus', '#!/bin/sh\nprintf "%s\\n" "ubus $*" >>"$MOCK_EVENTS"\n'
                     '[ "$2" != network.interface.f50 ] || printf \'{"up":true}\\n\'\nexit 0\n')
        self.command('jsonfilter', '#!/usr/bin/env python3\nimport json,sys\n'
                     'try: print(str(json.load(sys.stdin).get("up", False)).lower())\n'
                     'except Exception: pass\n')
        self.command('ethtool', '#!/bin/sh\ncat "$MOCK_BASE/ethtool-$1" 2>/dev/null\n')

    def command(self, name, contents):
        path = self.bin / name
        path.write_text(contents)
        path.chmod(0o755)

    def data(self):
        return json.loads(self.uci_file.read_text())

    def update(self, values):
        current = self.data()
        current.update(values)
        self.uci_file.write_text(json.dumps(current))

    def run_script(self, script, *args):
        result = subprocess.run(['sh', str(script), *args], env=self.env,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def add_usb(self, vendor='19d2', name='usb0', driver='cdc_ether'):
        interface = self.net / name
        interface.mkdir()
        device = self.base / ('sys/devices/usb1/' + name + '/' + name + ':1.0')
        device.mkdir(parents=True, exist_ok=True)
        (device.parent / 'idVendor').write_text(vendor)
        (device.parent / 'speed').write_text('5000')
        driver_path = self.base / 'sys/bus/usb/drivers' / driver
        driver_path.mkdir(parents=True, exist_ok=True)
        (device / 'driver').symlink_to(driver_path, target_is_directory=True)
        (interface / 'device').symlink_to(device, target_is_directory=True)
        return name

    def add_port(self, name, carrier, speed, duplex='full'):
        path = self.net / name
        path.mkdir()
        for filename, value in [('carrier', carrier), ('speed', speed), ('duplex', duplex)]:
            if value is not None:
                (path / filename).write_text(str(value))

    def test_enable_binds_f50_and_does_not_duplicate_firewall_membership(self):
        self.add_usb()
        self.run_script(USB)
        self.run_script(USB, 'usb0')
        state = self.data()
        self.assertEqual(state['network.f50.device'], 'usb0')
        self.assertEqual(state['network.f50.proto'], 'dhcp')
        self.assertEqual(state['network.f50.auto'], '1')
        self.assertEqual(state['firewall.@zone[0].network'].split().count('f50'), 1)
        self.assertIn('ifup f50', self.events.read_text())

    def test_disable_survives_hotplug_and_can_be_reenabled(self):
        self.add_usb()
        self.update({'arthur.usb.enabled': '0', 'network.f50': 'interface',
                     'network.f50.device': 'usb0', 'network.f50.auto': '1'})
        self.run_script(USB, 'usb0')
        self.run_script(USB)
        self.assertEqual(self.data()['network.f50.auto'], '0')
        self.assertNotIn('ifup f50', self.events.read_text())
        self.assertIn('ifdown f50', self.events.read_text())
        self.update({'arthur.usb.enabled': '1'})
        self.run_script(USB)
        self.assertEqual(self.data()['network.f50.auto'], '1')
        self.assertIn('ifup f50', self.events.read_text())

    def test_disabled_before_first_connection_does_not_create_uplink(self):
        self.add_usb()
        self.update({'arthur.usb.enabled': '0'})
        self.run_script(USB, 'usb0')
        self.assertNotIn('network.f50', self.data())

    def test_ethernet_adapters_and_invalid_device_names_are_ignored(self):
        self.add_usb(vendor='0bda', driver='r8152')
        self.run_script(USB, 'usb0')
        self.run_script(USB, '../../bad;command')
        self.assertNotIn('network.f50', self.data())

    def test_other_brands_shared_networks_work_and_qmi_is_not_forced_to_dhcp(self):
        for driver in ('cdc_ether', 'rndis_host', 'cdc_ncm'):
            name = 'tether-' + driver
            self.add_usb(vendor='12d1', name=name, driver=driver)
            # Keep an explicitly configured adapter stable during a second hotplug.
            self.update({'network.f50.device': name})
            self.run_script(USB, name)
            self.assertEqual(self.data()['network.f50.device'], name)
        self.add_usb(vendor='19d2', name='wwan0', driver='qmi_wwan')
        # Remove configured matching interfaces so only the unsupported QMI candidate remains.
        self.update({'network.f50.device': ''})
        self.run_script(USB, 'wwan0')
        self.assertEqual(self.data()['network.f50.device'], '')

    def test_second_tether_does_not_steal_configured_working_uplink(self):
        self.add_usb(name='usb0')
        self.add_usb(vendor='12d1', name='usb1', driver='rndis_host')
        self.update({'network.f50.device': 'usb0'})
        self.run_script(USB, 'usb1')
        self.assertEqual(self.data()['network.f50.device'], 'usb0')

    def test_link_report_distinguishes_1000_100_disconnected_and_missing(self):
        self.add_port('wan', 1, 1000)
        self.add_port('lan1', 1, 100, 'half')
        self.add_port('lan2', 0, 1000)
        self.add_usb()
        self.update({'network.f50.device': 'usb0'})
        data = json.loads(self.run_script(STATUS, 'call', 'status'))
        self.assertEqual([port['label'] for port in data['ports']], ['WAN', 'LAN1', 'LAN2', 'LAN3'])
        self.assertEqual(data['ports'][0]['speed'], 1000)
        self.assertEqual(data['ports'][1]['speed'], 100)
        self.assertEqual(data['ports'][1]['duplex'], 'half')
        self.assertFalse(data['ports'][2]['link'])
        self.assertIsNone(data['ports'][2]['speed'])
        self.assertFalse(data['ports'][3]['present'])
        # USB presence must not be overwritten by the missing LAN3 status.
        self.assertTrue(data['usb_present'])
        self.assertTrue(data['usb_up'])

    def test_ethtool_fallback_and_unknown_speed(self):
        self.add_port('wan', None, None, None)
        (self.base / 'ethtool-wan').write_text('Settings for wan:\n Speed: 100Mb/s\n Duplex: Half\n Link detected: yes\n')
        self.add_port('lan1', 1, -1)
        ports = json.loads(self.run_script(STATUS, 'call', 'status'))['ports']
        self.assertEqual(ports[0]['speed'], 100)
        self.assertEqual(ports[0]['duplex'], 'half')
        self.assertTrue(ports[1]['link'])
        self.assertIsNone(ports[1]['speed'])

    def wifi_defaults(self):
        self.update({
            'wireless.radio0': 'wifi-device', 'wireless.radio0.band': '2g',
            'wireless.radio1': 'wifi-device', 'wireless.radio1.band': '5g',
            'wireless.default_radio0': 'wifi-iface', 'wireless.default_radio0.device': 'radio0',
            'wireless.default_radio0.mode': 'ap', 'wireless.default_radio0.ssid': 'LibWrt',
            'wireless.default_radio0.encryption': 'none',
            'wireless.default_radio1': 'wifi-iface', 'wireless.default_radio1.device': 'radio1',
            'wireless.default_radio1.mode': 'ap', 'wireless.default_radio1.ssid': 'LibWrt',
            'wireless.default_radio1.encryption': 'none',
            'wireless.custom': 'wifi-iface', 'wireless.custom.device': 'radio0',
            'wireless.custom.mode': 'ap', 'wireless.custom.ssid': 'ExistingWifi',
            'wireless.custom.key': 'keep-this-password', 'wireless.custom.encryption': 'psk2'
        })
    def test_wifi_sets_requested_defaults_and_preserves_custom_networks(self):
        self.wifi_defaults()
        self.run_script(WIFI)
        data = self.data()
        key = data['wireless.default_radio0.key']
        self.assertEqual(key, 'jdy-cookorz2.4G')
        self.assertEqual(data['wireless.default_radio1.key'], 'jdy-cookorz5G')
        self.assertEqual(data['wireless.default_radio0.ssid'], key)
        self.assertEqual(data['wireless.default_radio1.ssid'], 'jdy-cookorz5G')
        self.assertEqual(data['wireless.radio1.disabled'], '0')
        self.assertEqual(data['wireless.default_radio0.encryption'], 'psk2')
        self.assertEqual(data['wireless.default_radio1.network'], 'lan')
        self.assertEqual(data['wireless.default_radio1.hidden'], '0')
        self.assertEqual(data['wireless.radio0.channel'], '1')
        self.assertEqual(data['wireless.radio1.channel'], '36')
        self.assertEqual(data['wireless.radio1.country'], 'CN')
        self.assertEqual(data['wireless.radio0.htmode'], 'HE20')
        self.assertEqual(data['wireless.radio1.htmode'], 'HE80')
        self.assertEqual(data['wireless.custom.key'], 'keep-this-password')
        self.run_script(WIFI)
        self.assertEqual(self.data()['wireless.default_radio0.key'], key)

    def test_wifi_waits_for_both_bands_then_retries_without_losing_setup(self):
        self.wifi_defaults()
        current = self.data()
        del current['wireless.radio1.band']
        self.uci_file.write_text(json.dumps(current))
        result = subprocess.run(['sh', str(WIFI)], env=self.env, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('wireless.default_radio0.key', self.data())
        self.update({'wireless.radio1.band': '5g'})
        self.run_script(WIFI)
        self.assertEqual(self.data()['wireless.default_radio1.ssid'], 'jdy-cookorz5G')

    def test_usb_bus_and_driver_speed_are_independent_even_when_disabled(self):
        self.add_usb()
        self.update({'arthur.usb.enabled': '0'})
        interface = self.net / 'usb0'
        (interface / 'carrier').write_text('1')
        (interface / 'speed').write_text('1000')
        data = json.loads(self.run_script(STATUS, 'call', 'status'))
        self.assertFalse(data['usb_enabled'])
        self.assertTrue(data['usb_present'])
        self.assertEqual(data['usb_bus_speed'], 5000)
        self.assertEqual(data['usb_port']['speed'], 1000)
        self.assertEqual(data['usb_port']['device'], 'usb0')
        (interface / 'speed').write_text('-1')
        (self.base / 'sys/devices/usb1/usb0/speed').write_text('480')
        data = json.loads(self.run_script(STATUS, 'call', 'status'))
        self.assertEqual(data['usb_bus_speed'], 480)
        self.assertIsNone(data['usb_port']['speed'])

    def test_usb_missing_or_unreadable_bus_does_not_invent_speed(self):
        data = json.loads(self.run_script(STATUS, 'call', 'status'))
        self.assertFalse(data['usb_present'])
        self.assertFalse(data['usb_port']['present'])
        self.assertIsNone(data['usb_bus_speed'])
        self.add_usb()
        (self.base / 'sys/devices/usb1/usb0/speed').write_text('unknown')
        data = json.loads(self.run_script(STATUS, 'call', 'status'))
        self.assertTrue(data['usb_present'])
        self.assertIsNone(data['usb_bus_speed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
