"""Publish a manually requested release only after every uploaded asset is verified."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def gh(*args, allow_missing=False):
    p = subprocess.run(['gh', *args], text=True, capture_output=True)
    if p.returncode:
        if allow_missing and ('HTTP 404' in p.stderr or 'release not found' in p.stderr.lower()):
            return None
        raise RuntimeError('GitHub operation failed: ' + p.stderr.strip())
    return p.stdout


def validated_assets(output, commit):
    data = json.loads((output/'FIRMWARE_VERSION.json').read_text())
    if not re.fullmatch(r'[a-f0-9]{40}', commit) or data['source_commit'] != commit:
        raise ValueError('Release commit differs from the built firmware')
    version = data['version']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[1-9][0-9]*)?', version) or data['tag'] != 'v'+version:
        raise ValueError('Invalid release version/tag')
    if data['prerelease'] != ('-rc.' in version):
        raise ValueError('Prerelease label differs from VERSION')
    images = data['images']
    if len(images) != 2 or {i['type'] for i in images} != {'factory','sysupgrade'}:
        raise ValueError('Both firmware variants must be present')
    sums = dict((name.strip(), digest) for digest,name in (line.split(None,1) for line in (output/'SHA256SUMS').read_text().splitlines()))
    assets = []
    for item in images:
        name = item['name']
        expected = f'jdy-cookorz-arthur-v{version}-{commit[:12]}-{item["type"]}.bin'
        if name != expected:
            raise ValueError('Unexpected firmware filename')
        path = output/name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size != item['size_bytes'] or digest != item['sha256'] or sums.get(name) != digest:
            raise ValueError('Firmware checksum/size mismatch')
        assets.append(path)
    for name in ('FIRMWARE_VERSION.json','SHA256SUMS','VERSION','CHANGELOG.md','RELEASE_NOTES.md','feature-checks.json','versions.env','feeds.lock.json','feed-revisions.txt','core-version.json','resolved.config','config.diff'):
        path = output/name
        if not path.is_file(): raise ValueError('Missing release record: '+name)
        assets.append(path)
    if (output/'VERSION').read_text().strip() != version:
        raise ValueError('VERSION record differs from manifest')
    return data, assets


def publish(output, commit, repository):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository name')
    data, assets = validated_assets(output, commit)
    tag = data['tag']
    if gh('release','view',tag,'--repo',repository,allow_missing=True) is not None:
        raise ValueError('Version already exists; refusing to replace its release')
    if gh('api',f'repos/{repository}/git/ref/tags/{tag}',allow_missing=True) is not None:
        raise ValueError('Tag already exists; choose a new version after reviewing the old tag')
    gh('release','create',tag,*map(str,assets),'--repo',repository,'--target',commit,
       '--title',f'jdy-cookorz {tag} · by-cookorz','--notes-file',str(output/'RELEASE_NOTES.md'),'--draft')
    drafts = json.loads(gh('api',f'repos/{repository}/releases?per_page=100'))
    matches = [item for item in drafts if item['tag_name'] == tag and item['draft']]
    if len(matches) != 1:
        raise ValueError('Draft release could not be uniquely identified')
    uploaded = json.loads(gh('api',f'repos/{repository}/releases/{matches[0]["id"]}'))
    entries = {entry['name']: entry for entry in uploaded['assets']}
    for path in assets:
        entry = entries.get(path.name)
        if not entry or entry['size'] != path.stat().st_size:
            raise ValueError('Draft kept: uploaded assets are incomplete')
        digest = entry.get('digest')
        if digest and digest != 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Draft kept: uploaded asset hash differs')
    gh('release','edit',tag,'--repo',repository,'--draft=false',
       '--prerelease='+str(data['prerelease']).lower(), '--latest='+str(not data['prerelease']).lower())


if __name__ == '__main__':
    publish(Path(sys.argv[1]), os.environ['GITHUB_SHA'], os.environ['GITHUB_REPOSITORY'])
