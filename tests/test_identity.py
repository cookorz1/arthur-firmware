"""Exercise identity persistence and rejected uploads without touching the host."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'package/arthur/files/usr/libexec/arthur-identity'
MOCK=r'''#!/usr/bin/env python3
import json,os,pathlib,sys
root=pathlib.Path(os.environ['ARTHUR_IDENTITY_ROOT']);a=sys.argv[1:]
if pathlib.Path(sys.argv[0]).name=='uci':
    if 'get' in a:print((root/'hostname').read_text())
    elif a[0]=='set':(root/'hostname').write_text(a[1].split('=',1)[1])
    elif a[0]!='commit':sys.exit(1)
else:
    if a[0]=='load':
        try:json.loads(a[1])
        except Exception:sys.exit(1)
        (root/'request').write_text(a[1])
    elif a[0]=='get':
        v=json.loads((root/'request').read_text()).get(a[1],'')
        print(int(v) if isinstance(v,bool) else v)
    elif a[0]=='init':(root/'response').write_text('{}')
    elif a[0]=='add':
        d=json.loads((root/'response').read_text());d[a[2]]=a[3]=='1' if a[1]=='boolean' else a[3];(root/'response').write_text(json.dumps(d))
    elif a[0]=='dump':print((root/'response').read_text())
'''

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);b=self.root/'bin';b.mkdir()
        for name in ('uci','identity_json'):
            f=b/name;f.write_text(MOCK);f.chmod(0o755)
        (self.root/'hostname').write_text('jdy-cookorz')
        lib=self.root/'jshn.sh';lib.write_text('''json_load() { identity_json load "$1"; }
json_get_var() { local v; v="$(identity_json get "$2")"; export "$1=$v"; }
json_init() { identity_json init; }
json_add_string() { identity_json add string "$1" "$2"; }
json_add_boolean() { identity_json add boolean "$1" "$2"; }
json_dump() { identity_json dump; }
''')
        self.env=dict(os.environ,PATH=str(b)+os.pathsep+os.environ['PATH'],ARTHUR_IDENTITY_ROOT=str(self.root),ARTHUR_JSHN_LIB=str(lib))
        self.png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=')
    def run_script(self,mode='save',**data):
        r=subprocess.run(['sh',str(SCRIPT),mode],input=json.dumps(data),capture_output=True,text=True,env=self.env,timeout=15)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads(r.stdout) if r.stdout else None
    def save(self,**kw):
        return self.run_script(hostname=kw.pop('hostname','my-router'),**kw)
    def test_upload_publish_reboot_and_reset(self):
        result=self.save(image=base64.b64encode(self.png).decode(),reset=False)
        self.assertEqual(result,{'hostname':'my-router','custom_logo':True})
        self.assertEqual((self.root/'etc/arthur/logo.png').read_bytes(),self.png)
        public=self.root/'www/luci-static/arthur/identity.json'
        self.assertIn('custom-logo.png?v=',public.read_text())
        self.run_script('publish');self.assertIn('my-router',public.read_text())
        self.save(hostname='router2',image='',reset=False)
        self.assertTrue((self.root/'etc/arthur/logo.png').exists())
        self.save(image='',reset=True)
        self.assertFalse((self.root/'etc/arthur/logo.png').exists())
        self.assertIn('avatar.jpg',public.read_text())
    def test_rejected_names_do_not_change_saved_state(self):
        for name in ('','-bad','bad-','a.b','a b','a;reboot','<script>','a'*64):
            self.assertIn('error',self.save(hostname=name))
            self.assertEqual((self.root/'hostname').read_text(),'jdy-cookorz')
    def test_reject_invalid_oversized_and_incomplete_images(self):
        for image in ('%%%','abcd',base64.b64encode(b'<svg onload="alert(1)"/>').decode(),base64.b64encode(self.png[:-1]).decode(),base64.b64encode(self.png+b'x'*262144).decode()):
            self.assertIn('error',self.save(image=image))
            self.assertEqual((self.root/'hostname').read_text(),'jdy-cookorz')
            self.assertFalse((self.root/'etc/arthur/logo.png').exists())
    def test_reject_dimensions_and_conflicting_actions(self):
        png=self.png[:16]+(4096).to_bytes(4,'big')+self.png[20:]
        self.assertIn('error',self.save(image=base64.b64encode(png).decode()))
        self.assertIn('error',self.save(image=base64.b64encode(self.png).decode(),reset=True))
    def test_write_is_acl_protected_and_backup_path_is_registered(self):
        acl=json.loads((ROOT/'package/arthur/files/usr/share/rpcd/acl.d/luci-app-arthur.json').read_text())['luci-app-arthur']
        self.assertIn('save_identity',acl['write']['ubus']['arthur'])
        self.assertNotIn('save_identity',acl['read']['ubus']['arthur'])
        self.assertEqual((ROOT/'package/arthur/files/lib/upgrade/keep.d/arthur-identity').read_text(),'/etc/arthur/\n')
        r=subprocess.run(['sh',str(ROOT/'package/arthur/files/usr/libexec/rpcd/arthur'),'list'],capture_output=True,text=True)
        self.assertEqual(json.loads(r.stdout)['save_identity']['reset'],'Boolean')

if __name__=='__main__':unittest.main()
