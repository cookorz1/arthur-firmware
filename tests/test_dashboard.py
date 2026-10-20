"""Read-only dashboard snapshots with isolated command/sysfs fixtures."""
import json
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'package/arthur/files/usr/libexec/arthur-dashboard'
MOCK=r'''#!/usr/bin/env python3
import json,os,pathlib,sys
root=pathlib.Path(os.environ['MOCK_DASH'])
name=pathlib.Path(sys.argv[0]).name
args=sys.argv[1:]
if name=='jshn_event':
    file=root/'json-events'
    if args[0]=='dump':
        stack=[{}]
        for event in file.read_text().splitlines():
            kind,key,*rest=json.loads(event)
            if kind=='close': stack.pop();continue
            value={} if kind=='object' else [] if kind=='array' else None if kind=='null' else float(rest[0]) if kind=='double' else rest[0]=='1' if kind=='boolean' else rest[0]
            if isinstance(stack[-1],list):stack[-1].append(value)
            else:stack[-1][key]=value
            if kind in ('object','array'):stack.append(value)
        print(json.dumps(stack[0]))
    else:
        with file.open('a') as s:s.write(json.dumps(args)+'\n')
elif name=='ubus':
    print((root/(args[1].split('.')[-1]+'.json')).read_text())
elif name=='jsonfilter':
    data=json.loads(args[args.index('-s')+1]);key=args[-1]
    value=data.get(key[2:],'') if key in ('@.up','@.l3_device') else (data.get('ipv4-address' if 'ipv4' in key else 'ipv6-address') or [{}])[0].get('address','')
    print(str(value).lower() if isinstance(value,bool) else value)
elif name=='df':print('Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/loop0 2097152 100000 1997152 5% /overlay')
elif name=='ip':print('192.168.10.2 lladdr 00:11:22:33:44:55 REACHABLE\n192.168.10.3 lladdr 00:11:22:33:44:56 STALE\n192.168.10.4 FAILED')
else:raise SystemExit('Unexpected command '+name)
'''


@unittest.skipIf(os.name=='nt','Shell snapshots run in Linux CI')
class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);bin=self.root/'bin';bin.mkdir()
        proc=self.root/'proc';proc.mkdir();(proc/'uptime').write_text('100.25 320.00\n');(proc/'stat').write_text('cpu  10 20 30 100 5 2 3 4 50 50\n')
        net=self.root/'net';net.mkdir()
        for dev in ('wan','usb0'):
            p=net/dev/'statistics';p.mkdir(parents=True);(p/'rx_bytes').write_text('123456');(p/'tx_bytes').write_text('7890')
        for interface,dev in [('wan','wan'),('f50','usb0'),('lan','br-lan')]:
            (self.root/(interface+'.json')).write_text(json.dumps({'up':True,'l3_device':dev,'ipv4-address':[{'address':'192.0.2.2'}]}))
        (self.root/'leases').write_text('0 00:11:22:33:44:55 192.168.10.2 name-with-"quote *\n')
        for name in ('ubus','jsonfilter','df','ip','jshn_event'):
            path=bin/name;path.write_text(MOCK);path.chmod(0o755)
        library=self.root/'jshn.sh'
        library.write_text('json_init() { : >"$MOCK_DASH/json-events"; }\n'
                           'json_add_object() { jshn_event object "$1"; }\njson_add_array() { jshn_event array "$1"; }\n'
                           'json_close_object() { jshn_event close ""; }\njson_close_array() { jshn_event close ""; }\n'
                           'json_dump() { jshn_event dump; }\n'+''.join('json_add_'+kind+'() { jshn_event '+kind+' "$1" "$2"; }\n' for kind in ('string','double','boolean','null')))
        self.env=dict(os.environ,PATH=str(bin)+os.pathsep+os.environ['PATH'],MOCK_DASH=str(self.root),ARTHUR_PROC_ROOT=str(proc),ARTHUR_SYSFS_ROOT=str(net),ARTHUR_JSHN_LIB=str(library),ARTHUR_DHCP_LEASES=str(self.root/'leases'))

    def snapshot(self):
        p=subprocess.run(['sh',str(SCRIPT)],env=self.env,text=True,capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        return json.loads(p.stdout)

    def test_ticks_counters_overlay_and_cached_neighbors_are_actual_values(self):
        s=self.snapshot()
        self.assertEqual(s['sample_time'],100.25)
        self.assertEqual(s['cpu'],{'total':174,'idle':105})
        self.assertEqual(s['storage']['total_kib'],2097152)
        self.assertEqual(s['uplinks'][0]['rx_bytes'],123456)
        self.assertEqual(s['uplinks'][1]['device'],'usb0')
        self.assertEqual([c['state'] for c in s['clients']],['REACHABLE','STALE'])
        self.assertEqual(s['clients'][0]['hostname'],'name-with-"quote')

    def test_disconnected_interfaces_do_not_claim_ready_and_missing_counters_are_null(self):
        (self.root/'f50.json').write_text(json.dumps({'up':False}))
        s=self.snapshot()
        self.assertFalse(s['uplinks'][1]['ready'])
        self.assertIsNone(s['uplinks'][1]['rx_bytes'])

    def test_invalid_device_names_are_never_used_as_paths(self):
        (self.root/'wan.json').write_text(json.dumps({'up':True,'l3_device':'../../outside','ipv4-address':[{'address':'192.0.2.2'}]}))
        s=self.snapshot()
        self.assertEqual(s['uplinks'][0]['device'],'')
        self.assertIsNone(s['uplinks'][0]['rx_bytes'])
