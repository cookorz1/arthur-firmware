import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('archive', ROOT/'.github/scripts/archive_releases.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.item = copy.deepcopy(archive.read_plan(ROOT/'.github/release-archive.json')['releases'][3])

    def make_archive(self, corrupt=False, unsafe=False):
        images = {f'libwrt-jdcloud_re-ss-01-squashfs-{kind}.bin': ('fixture-'+kind).encode()
                  for kind in ('factory', 'sysupgrade')}
        sums = ''.join(hashlib.sha256(content).hexdigest()+'  '+name+'\n' for name, content in images.items())
        path = self.root/'original.zip'
        with zipfile.ZipFile(path, 'w') as output:
            for name, content in images.items():
                output.writestr(name, content + (b'changed' if corrupt else b''))
            output.writestr('SHA256SUMS', sums)
            output.writestr('versions.env', 'SOURCE_COMMIT=original\n')
            output.writestr('device.manifest', 'luci-app-arthur - 1.2.0-r1\n')
            if unsafe: output.writestr('../escape', 'not allowed')
        self.item['artifact_sha256'] = archive.digest(path)
        return path, images, sums

    def test_checked_in_plan_identifies_all_seven_successful_builds(self):
        plan = archive.read_plan(ROOT/'.github/release-archive.json')
        self.assertEqual([x['run_number'] for x in plan['releases']], [4,5,6,7,8,12,14])
        self.assertEqual(plan['releases'][-1]['tag'], 'v1.5.0-rc.2')

    def test_only_the_pinned_successful_run_and_artifact_are_accepted(self):
        i=self.item
        run={'id':i['run_id'],'run_number':i['run_number'],'status':'completed','conclusion':'success','head_sha':i['source_commit']}
        artifact={'id':i['artifact_id'],'name':i['artifact_name'],'expired':False,'digest':'sha256:'+i['artifact_sha256'],
                  'workflow_run':{'id':i['run_id'],'head_sha':i['source_commit']}}
        archive.verify_origin(i,run,artifact)
        for changes in ({'head_sha':'a'*40},{'conclusion':'cancelled'},{'status':'in_progress'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                archive.verify_origin(i,dict(run,**changes),artifact)
        for changes in ({'expired':True},{'digest':'sha256:'+'0'*64},{'workflow_run':{'id':1}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                archive.verify_origin(i,run,dict(artifact,**changes))

    def test_extract_preserves_original_images_and_checksum_record(self):
        path, images, sums=self.make_archive()
        output=self.root/'output'
        archive.extract_verified(self.item,path,output)
        self.assertEqual((output/'SHA256SUMS').read_text(),sums)
        for name,content in images.items(): self.assertEqual((output/name).read_bytes(),content)

    def test_bad_archive_digest_stops_before_extracting(self):
        path,_,_=self.make_archive();self.item['artifact_sha256']='0'*64
        with self.assertRaises(ValueError): archive.extract_verified(self.item,path,self.root/'output')
        self.assertFalse((self.root/'output').exists())

    def test_changed_firmware_is_rejected_even_if_zip_digest_matches(self):
        path,_,_=self.make_archive(corrupt=True)
        with self.assertRaisesRegex(ValueError,'firmware checksum'): archive.extract_verified(self.item,path,self.root/'output')

    def test_unsafe_zip_paths_never_escape_the_destination(self):
        path,_,_=self.make_archive(unsafe=True)
        with self.assertRaisesRegex(ValueError,'Unsafe'): archive.extract_verified(self.item,path,self.root/'output')
        self.assertFalse((self.root/'escape').exists())

    def test_existing_tag_must_point_to_the_original_source(self):
        with patch.object(archive,'api',return_value={'object':{'type':'commit','sha':'0'*40}}), self.assertRaises(ValueError):
            archive.verify_tag('cookorz1/arthur-firmware',self.item['tag'],self.item['source_commit'])

    def fake_publication(self, partial=False, published=False, wrong_source=False):
        paths=[]
        for name in ('factory.bin','SHA256SUMS'):
            p=self.root/name;p.write_bytes(name.encode());paths.append(p)
        note=self.root/'notes.md';note.write_text('Fixture release notes\n')
        uploaded=[{'name':p.name,'size':p.stat().st_size,'digest':'sha256:'+archive.digest(p)} for p in paths]
        state={'exists':published,'draft':not published,'uploaded':uploaded if published else []}
        calls=[]
        def api(path,allow_missing=False):
            if '/git/ref/tags/' in path:
                return None if state['draft'] else {'object':{'type':'commit','sha':self.item['source_commit']}}
            if path.endswith('/releases?per_page=100'):
                return [] if not state['exists'] else [{'id':12,'tag_name':self.item['tag'],'draft':state['draft'],
                    'prerelease':not state['draft'],'target_commitish':'0'*40 if wrong_source else self.item['source_commit'],
                    'name':self.item['title'],'body':'Fixture release notes\n'}]
            if '/assets?' in path:return state['uploaded']
            raise AssertionError(path)
        def command(*args,**kwargs):
            calls.append(args)
            if args[:2]==('release','create'):state['exists']=True
            elif args[:2]==('release','upload'):state['uploaded']=uploaded[:1] if partial else uploaded
            elif args[:2]==('release','edit'):state['draft']=False
            else:raise AssertionError(args)
        return paths,note,state,calls,api,command

    def test_draft_is_published_only_after_all_uploaded_assets_match(self):
        paths,note,state,calls,api,command=self.fake_publication()
        with patch.object(archive,'api',side_effect=api),patch.object(archive,'command',side_effect=command):
            archive.publish(self.item,paths,note,'cookorz1/arthur-firmware')
        self.assertFalse(state['draft'])
        self.assertEqual([c[1] for c in calls],['create','upload','edit'])
        self.assertIn('--prerelease=true',calls[-1]);self.assertIn('--latest=false',calls[-1])

    def test_partial_upload_retains_draft_and_never_publishes(self):
        paths,note,state,calls,api,command=self.fake_publication(partial=True)
        with patch.object(archive,'api',side_effect=api),patch.object(archive,'command',side_effect=command),self.assertRaisesRegex(ValueError,'incomplete'):
            archive.publish(self.item,paths,note,'cookorz1/arthur-firmware')
        self.assertTrue(state['draft']);self.assertNotIn('edit',[c[1] for c in calls])

    def test_verified_existing_release_is_not_modified(self):
        paths,note,state,calls,api,command=self.fake_publication(published=True)
        with patch.object(archive,'api',side_effect=api),patch.object(archive,'command',side_effect=command):
            archive.publish(self.item,paths,note,'cookorz1/arthur-firmware')
        self.assertEqual(calls,[])

    def test_existing_release_from_another_commit_is_never_changed(self):
        paths,note,state,calls,api,command=self.fake_publication(published=True,wrong_source=True)
        with patch.object(archive,'api',side_effect=api),patch.object(archive,'command',side_effect=command),self.assertRaises(ValueError):
            archive.publish(self.item,paths,note,'cookorz1/arthur-firmware')
        self.assertEqual(calls,[])
