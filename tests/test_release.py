import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
release=module('firmware_release');publisher=module('publish_release')
COMMIT='a'*40


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir();self.output=self.root/'output';self.output.mkdir()
        for name in ('VERSION','CHANGELOG.md','versions.env','feeds.lock.json','package/arthur/Makefile'):
            p=self.project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text((ROOT/name).read_text())
        (self.project/'VERSION').write_text('1.5.0-rc.1\n')
        (self.project/'CHANGELOG.md').write_text('## [1.5.0-rc.1] - 2026-10-21\n\n- Fixture release notes.\n')
        (self.project/'package/arthur/Makefile').write_text('PKG_VERSION:=1.5.0\n')

    def images(self):
        import hashlib
        sums=[]
        for kind in ('factory','sysupgrade'):
            p=self.output/f'libwrt-jdcloud_re-ss-01-squashfs-{kind}.bin';p.write_bytes(('fixture-'+kind).encode());sums.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
        (self.output/'SHA256SUMS').write_text('\n'.join(sums)+'\n')

    def prepared(self):
        self.images();data=release.prepare(self.project,self.output,COMMIT)
        for name in ('feature-checks.json','versions.env','feeds.lock.json','feed-revisions.txt','core-version.json','resolved.config','config.diff'):
            (self.output/name).write_text('{}')
        return data

    def test_version_requires_matching_package_changelog_and_tag(self):
        self.assertEqual(release.check(self.project,{}),'1.5.0-rc.1')
        with self.assertRaises(ValueError):release.check(self.project,{'GITHUB_REF_TYPE':'tag','GITHUB_REF_NAME':'v9.0.0'})
        (self.project/'VERSION').write_text('1.5.1')
        with self.assertRaises(ValueError):release.check(self.project,{})

    def test_stamp_records_version_author_and_full_commit(self):
        release.stamp(self.project,self.root/'source',COMMIT)
        self.assertEqual((self.root/'source/files/etc/arthur-version').read_text().strip(),'1.5.0-rc.1')
        data=json.loads((self.root/'source/files/etc/arthur-release.json').read_text());self.assertEqual(data['author'],'by-cookorz');self.assertEqual(data['source_commit'],COMMIT)

    def test_prepare_preserves_bytes_and_links_names_hashes_and_source(self):
        data=self.prepared();record,assets=publisher.validated_assets(self.output,COMMIT)
        self.assertEqual(record['version'],'1.5.0-rc.1');self.assertEqual({i['type'] for i in record['images']},{'factory','sysupgrade'})
        self.assertEqual(data['source_commit'],COMMIT);self.assertEqual(len([p for p in assets if p.suffix=='.bin']),2)
        self.assertIn(COMMIT,(self.output/'RELEASE_NOTES.md').read_text())
        self.assertIn('by-cookorz',(self.output/'RELEASE_NOTES.md').read_text())

    def test_corrupt_image_stops_before_renaming_or_publishing(self):
        self.images();p=next(self.output.glob('*factory.bin'));p.write_bytes(b'corrupt')
        with self.assertRaises(ValueError):release.prepare(self.project,self.output,COMMIT)
        self.assertTrue(p.exists());self.assertFalse((self.output/'FIRMWARE_VERSION.json').exists())

    def test_publish_rechecks_checksums_and_commit(self):
        data=self.prepared()
        with self.assertRaises(ValueError):publisher.validated_assets(self.output,'b'*40)
        (self.output/data['images'][0]['name']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):publisher.validated_assets(self.output,COMMIT)

    def test_existing_release_is_never_overwritten(self):
        self.prepared()
        with patch.object(publisher,'gh',return_value='existing') as gh:
            with self.assertRaises(ValueError):publisher.publish(self.output,COMMIT,'cookorz1/arthur-firmware')
            self.assertEqual(gh.call_count,1)

    def test_publish_stays_draft_until_assets_pass_verification(self):
        import hashlib
        data=self.prepared();_,assets=publisher.validated_assets(self.output,COMMIT)
        responses=[None,None,json.dumps({'tag_name':data['tag'],'draft':True,'id':42,'target_commitish':COMMIT}),'uploaded',json.dumps({'assets':[{'name':p.name,'size':p.stat().st_size,'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()} for p in assets]}),'published']
        with patch.object(publisher,'gh',side_effect=responses) as gh:
            publisher.publish(self.output,COMMIT,'cookorz1/arthur-firmware')
            self.assertIn('POST',gh.call_args_list[2].args)
            self.assertEqual(gh.call_args_list[3].args[:2],('release','upload'))
            self.assertIn('--draft=false',gh.call_args_list[-1].args)
            self.assertIn('--prerelease=true',gh.call_args_list[-1].args)
            self.assertIn('--latest=false',gh.call_args_list[-1].args)

    def test_incomplete_upload_never_publishes(self):
        data=self.prepared()
        with patch.object(publisher,'gh',side_effect=[None,None,json.dumps({'tag_name':data['tag'],'draft':True,'id':42,'target_commitish':COMMIT}),'uploaded',json.dumps({'assets':[]})]) as gh:
            with self.assertRaises(ValueError):publisher.publish(self.output,COMMIT,'cookorz1/arthur-firmware')
            self.assertFalse(any('--draft=false' in call.args for call in gh.call_args_list))

    def test_push_publication_skips_existing_release_without_replacing_assets(self):
        self.prepared()
        with patch.object(publisher,'gh',return_value='existing') as gh:
            publisher.publish(self.output,COMMIT,'cookorz1/arthur-firmware',skip_existing=True)
            self.assertEqual(gh.call_count,1)

    def test_missing_server_digest_keeps_release_draft(self):
        data=self.prepared();_,assets=publisher.validated_assets(self.output,COMMIT)
        responses=[None,None,json.dumps({'tag_name':data['tag'],'draft':True,'id':42,'target_commitish':COMMIT}),'uploaded',json.dumps({'assets':[{'name':p.name,'size':p.stat().st_size} for p in assets]})]
        with patch.object(publisher,'gh',side_effect=responses) as gh:
            with self.assertRaises(ValueError): publisher.publish(self.output,COMMIT,'cookorz1/arthur-firmware')
            self.assertFalse(any('--draft=false' in call.args for call in gh.call_args_list))
