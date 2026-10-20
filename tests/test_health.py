"""Exercise manual uplink diagnostics with isolated commands, no public traffic."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEALTH = ROOT / 'package/arthur/files/usr/libexec/arthur-health'
MOCK = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['MOCK_HEALTH'])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / 'events').open('a') as stream:
    stream.write(json.dumps([name, *args]) + '\n')
if name == 'ubus':
    interface = args[args.index('call') + 1].split('.')[-1]
    print((root / (interface + '.json')).read_text())
elif name == 'jsonfilter':
    state = json.load(sys.stdin)
    value = {'@.up': state.get('up', False), '@.l3_device': state.get('l3_device', ''),
             '@["ipv4-address"][0].address': (state.get('ipv4-address') or [{}])[0].get('address', '')}[args[-1]]
    print(str(value).lower() if isinstance(value, bool) else value)
elif name == 'ping':
    device = args[args.index('-I') + 1]
    print((root / ('ping-' + device + '-' + args[-1])).read_text())
elif name == 'curl':
    device = args[args.index('--interface') + 1].removeprefix('if!')
    value = (root / ('curl-' + device)).read_text()
    if value == 'timeout': sys.exit(28)
    print(value, end='')
'''


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        bin_dir = self.root / 'bin'
        bin_dir.mkdir()
        for name in ('ubus', 'jsonfilter', 'ping', 'curl'):
            path = bin_dir / name
            path.write_text(MOCK)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
                        MOCK_HEALTH=str(self.root))
        self.interface('wan', 'wan')
        self.interface('f50', 'usb0')

    def interface(self, name, device, up=True, ipv4=True):
        state = {'up': up, 'l3_device': device}
        if ipv4:
            state['ipv4-address'] = [{'address': '192.0.2.2'}]
        (self.root / (name + '.json')).write_text(json.dumps(state))
        for target in ('223.5.5.5', '119.29.29.29'):
            (self.root / ('ping-' + device + '-' + target)).write_text(
                '3 packets transmitted, 3 received, 0% packet loss, time 2000ms\n'
                'rtt min/avg/max/mdev = 10.0/12.5/15.0/1.0 ms\n')
        (self.root / ('curl-' + device)).write_text('200')

    def run_probe(self):
        process = subprocess.run(['sh', str(HEALTH)], env=self.env,
                                 text=True, capture_output=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def test_uplinks_are_bound_separately_and_probes_are_bounded(self):
        (self.root / 'curl-usb0').write_text('timeout')
        (self.root / 'ping-usb0-223.5.5.5').write_text('3 packets transmitted, 0 received, 100% packet loss\n')
        data = self.run_probe()
        wan, usb = data['uplinks']
        self.assertTrue(wan['https'][0]['reachable'])
        self.assertEqual(wan['probes'][0]['latency'], 12.5)
        self.assertEqual(wan['probes'][0]['loss'], 0)
        self.assertFalse(usb['https'][0]['reachable'])
        self.assertEqual(usb['https'][0]['error_code'], 28)
        self.assertIsNone(usb['https'][0]['http_code'])
        self.assertEqual(usb['probes'][0]['loss'], 100)
        self.assertIsNone(usb['probes'][0]['latency'])
        events = [json.loads(line) for line in (self.root / 'events').read_text().splitlines()]
        for event in events:
            if event[0] == 'ping':
                self.assertIn(event[event.index('-I') + 1], ['wan', 'usb0'])
                self.assertEqual(event[event.index('-w') + 1], '4')
                self.assertEqual(event[event.index('-c') + 1], '3')
            if event[0] == 'curl':
                self.assertIn(event[event.index('--interface') + 1], ['if!wan', 'if!usb0'])
                self.assertEqual(event[event.index('--max-time') + 1], '4')

    def test_down_or_ipv6_only_interface_does_not_send_ipv4_probes(self):
        self.interface('wan', 'wan', up=False)
        self.interface('f50', 'usb0', ipv4=False)
        data = self.run_probe()
        self.assertFalse(data['uplinks'][0]['up'])
        self.assertFalse(data['uplinks'][1]['ready'])
        self.assertEqual(data['uplinks'][1]['probes'], [])
        events = (self.root / 'events').read_text()
        self.assertNotIn('"curl"', events)
        self.assertNotIn('"ping"', events)

    def test_missing_ping_statistics_are_unknown_not_zero_loss(self):
        (self.root / 'ping-wan-223.5.5.5').write_text('')
        data = self.run_probe()
        self.assertIsNone(data['uplinks'][0]['probes'][0]['loss'])
        self.assertIsNone(data['uplinks'][0]['probes'][0]['latency'])
