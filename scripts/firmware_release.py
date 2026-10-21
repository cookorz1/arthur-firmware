"""Validate project versions, stamp images, and prepare immutable release records."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re

VERSION_RE = r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-rc\.[1-9][0-9]*)?'


def read_version(project):
    version = (project / 'VERSION').read_text().strip()
    if not re.fullmatch(VERSION_RE, version):
        raise ValueError('Expected MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-rc.N')
    package = (project / 'package/arthur/Makefile').read_text()
    if f'PKG_VERSION:={version.split("-")[0]}\n' not in package:
        raise ValueError('Arthur package base version differs from VERSION')
    return version


def notes(project, version):
    text = (project / 'CHANGELOG.md').read_text(encoding='utf-8')
    match = re.search(r'^## \[' + re.escape(version) + r'\] - \d{4}-\d{2}-\d{2}\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not match or not match[1].strip():
        raise ValueError('Current version has no dated CHANGELOG entry')
    return match[1].strip()


def check(project, env=None):
    env = os.environ if env is None else env
    version = read_version(project)
    notes(project, version)
    if env.get('GITHUB_REF_TYPE') == 'tag' and env.get('GITHUB_REF_NAME') != 'v' + version:
        raise ValueError('Tag does not match VERSION; refusing to label this firmware')
    return version


def metadata(project, build_id):
    version = check(project)
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', build_id):
        raise ValueError('Invalid source build ID')
    return {'project': 'jdy-cookorz', 'author': 'by-cookorz', 'version': version,
            'tag': 'v' + version, 'prerelease': '-rc.' in version, 'source_commit': build_id,
            'build_number': os.environ.get('GITHUB_RUN_NUMBER', 'local'),
            'build_url': f'https://github.com/{os.environ.get("GITHUB_REPOSITORY", "cookorz1/arthur-firmware")}/actions/runs/{os.environ.get("GITHUB_RUN_ID", "")}',
            'built_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_pins': dict(line.split('=', 1) for line in (project/'versions.env').read_text().splitlines() if line and not line.startswith('#')),
            'feed_pins': json.loads((project/'feeds.lock.json').read_text()), 'hardware_testing': 'pending'}


def stamp(project, source, build_id):
    data = metadata(project, build_id)
    etc = source/'files/etc'; etc.mkdir(parents=True, exist_ok=True)
    (etc/'arthur-version').write_text(data['version'] + '\n')
    (etc/'arthur-release.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def prepare(project, output, build_id):
    data = metadata(project, build_id)
    output.mkdir(parents=True, exist_ok=True)
    images = sorted(output.glob('*jdcloud_re-ss-01*-factory.bin')) + sorted(output.glob('*jdcloud_re-ss-01*-sysupgrade.bin'))
    for kind in ('factory', 'sysupgrade'):
        if len([p for p in images if p.name.endswith('-'+kind+'.bin')]) != 1:
            raise ValueError('Exactly one verified '+kind+' image is required')
    sums = {}
    for line in (output/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split(None, 1); sums[name.strip()] = digest
    records = []
    destinations = []
    for image in images:
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if sums.get(image.name) != digest:
            raise ValueError('Firmware SHA256SUMS mismatch: '+image.name)
        kind = 'factory' if image.name.endswith('-factory.bin') else 'sysupgrade'
        name = f'jdy-cookorz-arthur-v{data["version"]}-{build_id[:12]}-{kind}.bin'
        destinations.append((image, output/name))
        records.append({'name': name, 'type': kind, 'size_bytes': image.stat().st_size, 'sha256': digest})
    for old, new in destinations:
        if new.exists():
            raise ValueError('Refusing to overwrite firmware: '+new.name)
    for old, new in destinations: old.rename(new)
    data['images'] = records
    (output/'FIRMWARE_VERSION.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (output/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['name']+'\n' for x in records))
    (output/'VERSION').write_text(data['version']+'\n')
    (output/'CHANGELOG.md').write_text((project/'CHANGELOG.md').read_text(encoding='utf-8'), encoding='utf-8')
    note = (f'# jdy-cookorz v{data["version"]} · by-cookorz\n\n' + notes(project, data['version']) +
            '\n\n## 下载与追踪\n\n- 设备：京东云亚瑟 AX1800 Pro / JDCloud RE-SS-01。\n'
            '- U-Boot 刷入选择 `factory.bin`；系统内升级选择 `sysupgrade.bin`。\n'
            '- `FIRMWARE_VERSION.json` 记录源码、上游版本和每个镜像的 SHA-256；与 `SHA256SUMS` 一同保存。\n'
            f'- 源码提交：`{build_id}`。\n- 构建记录：{data["build_url"]}。\n'
            '- 默认：192.168.10.1，root / password；保留配置升级时现有设置优先。\n'
            '- 实机验收状态：待验证。by-cookorz 负责固件定制与界面，上游为 LibWrt / LuCI / Argon。\n')
    (output/'RELEASE_NOTES.md').write_text(note, encoding='utf-8')
    return data


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('action', choices=['check','stamp','prepare']);p.add_argument('project',type=Path);p.add_argument('destination',type=Path,nargs='?');p.add_argument('build_id',nargs='?')
    a=p.parse_args()
    if a.action=='check': print(check(a.project))
    else:
        if a.destination is None or a.build_id is None: p.error('destination and build_id required')
        if a.action=='stamp': stamp(a.project,a.destination,a.build_id)
        else: prepare(a.project,a.destination,a.build_id)
