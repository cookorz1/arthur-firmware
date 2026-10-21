"""Archive verified successful builds without rebuilding or changing firmware bytes."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from publish_release import validated_assets


def command(*args, destination=None, allow_missing=False):
    with destination.open('wb') if destination else tempfile.TemporaryFile() as output:
        result = subprocess.run(['gh', *args], stdout=output, stderr=subprocess.PIPE)
        if result.returncode:
            error = result.stderr.decode('utf-8', errors='replace')
            if allow_missing and 'HTTP 404' in error:
                return None
            raise RuntimeError('GitHub operation failed: ' + error.strip())
        if destination:
            return ''
        output.seek(0)
        return output.read().decode('utf-8')


def api(path, allow_missing=False):
    text = command('api', path, allow_missing=allow_missing)
    return None if text is None else json.loads(text)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_plan(path):
    plan = json.loads(path.read_text(encoding='utf-8'))
    if plan.get('schema_version') != 1 or plan.get('repository') != 'cookorz1/arthur-firmware':
        raise ValueError('Unexpected archive repository/schema')
    if not plan.get('releases'):
        raise ValueError('Archive plan is empty')
    tags, artifacts = set(), set()
    for item in plan['releases']:
        if not re.fullmatch(r'(?:v[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[1-9][0-9]*)?|build-[1-9][0-9]*)', item['tag']):
            raise ValueError('Invalid archive tag')
        if item['tag'] in tags or item['artifact_id'] in artifacts:
            raise ValueError('Duplicate release/artifact')
        tags.add(item['tag']); artifacts.add(item['artifact_id'])
        if not re.fullmatch(r'[a-f0-9]{40}', item['source_commit']) or not re.fullmatch(r'[a-f0-9]{64}', item['artifact_sha256']):
            raise ValueError('Invalid pinned source/digest')
        if item['kind'] not in ('historical', 'versioned'):
            raise ValueError('Invalid archive kind')
        if item['version'] is not None and item['tag'] != 'v' + item['version']:
            raise ValueError('Version/tag mismatch')
        for name in ('run_id', 'run_number', 'artifact_id'):
            if type(item[name]) is not int or item[name] <= 0:
                raise ValueError('Invalid archive ID')
    return plan


def verify_origin(item, run, artifact):
    if (run.get('id') != item['run_id'] or run.get('run_number') != item['run_number'] or
            run.get('status') != 'completed' or run.get('conclusion') != 'success' or
            run.get('head_sha') != item['source_commit']):
        raise ValueError('Original run is not the pinned successful build')
    origin = artifact.get('workflow_run', {})
    if (artifact.get('id') != item['artifact_id'] or artifact.get('name') != item['artifact_name'] or
            artifact.get('expired') or artifact.get('digest') != 'sha256:' + item['artifact_sha256'] or
            origin.get('id') != item['run_id'] or origin.get('head_sha') != item['source_commit']):
        raise ValueError('Artifact does not belong to the pinned successful build')


def extract_verified(item, archive, output):
    if digest(archive) != item['artifact_sha256']:
        raise ValueError('Downloaded artifact ZIP digest mismatch')
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        if len(members) > 100 or sum(m.file_size for m in members) > 500 * 1024 * 1024:
            raise ValueError('Unexpected archive contents/size')
        names = set()
        for member in members:
            name = member.filename
            if (not re.fullmatch(r'[A-Za-z0-9_.+-]+', name) or name in ('.', '..') or
                    name in names or stat.S_ISLNK(member.external_attr >> 16)):
                raise ValueError('Unsafe or duplicate artifact path')
            names.add(name)
        output.mkdir(parents=True, exist_ok=False)
        for member in members:
            (output / member.filename).write_bytes(source.read(member))
    images = sorted(output.glob('*.bin'))
    if len(images) != 2 or {p.name.rsplit('-', 1)[-1] for p in images} != {'factory.bin', 'sysupgrade.bin'}:
        raise ValueError('Exactly one factory and one sysupgrade image required')
    if any(not ('jdcloud_re-ss-01' in p.name or p.name.startswith('jdy-cookorz-arthur-')) or
           p.stat().st_size == 0 or p.stat().st_size > 60 * 1024 * 1024 for p in images):
        raise ValueError('Unexpected Arthur image name/size')
    sums = {}
    for line in (output / 'SHA256SUMS').read_text().splitlines():
        value, name = line.split(None, 1)
        if name.strip() in sums or not re.fullmatch(r'[a-f0-9]{64}', value):
            raise ValueError('Invalid checksum record')
        sums[name.strip()] = value
    if set(sums) != {p.name for p in images} or any(sums[p.name] != digest(p) for p in images):
        raise ValueError('Original firmware checksum mismatch')
    if not list(output.glob('*.manifest')) or not (output / 'versions.env').is_file():
        raise ValueError('Original package/source records missing')
    if item['package_version']:
        manifests = '\n'.join(p.read_text() for p in output.glob('*.manifest'))
        if not re.search(r'^luci-app-arthur - ' + re.escape(item['package_version']) + r'(?:-[A-Za-z0-9.]+)?$', manifests, re.M):
            raise ValueError('Historical package version differs from archive plan')
    if item['kind'] == 'versioned':
        metadata, _ = validated_assets(output, item['source_commit'])
        if metadata['tag'] != item['tag'] or metadata['build_number'] != str(item['run_number']):
            raise ValueError('Versioned firmware provenance differs from archive plan')
    return images


def prepare(item, repository, working):
    run = api(f'repos/{repository}/actions/runs/{item["run_id"]}')
    artifact = api(f'repos/{repository}/actions/artifacts/{item["artifact_id"]}')
    verify_origin(item, run, artifact)
    archive = working / (item['tag'] + '.zip')
    command('api', f'repos/{repository}/actions/artifacts/{item["artifact_id"]}/zip', destination=archive)
    output = working / item['tag']
    images = extract_verified(item, archive, output)
    record = {
        'schema_version': 1, 'repository': repository, 'author': 'by-cookorz',
        'tag': item['tag'], 'kind': item['kind'], 'source_commit': item['source_commit'],
        'source_run_id': item['run_id'], 'source_run_number': item['run_number'],
        'source_run_url': run['html_url'], 'source_run_created_at': run['created_at'],
        'source_artifact_id': item['artifact_id'], 'source_artifact_name': item['artifact_name'],
        'source_artifact_sha256': item['artifact_sha256'],
        'project_version': item['version'] if item['kind'] == 'versioned' else None,
        'historical_package_version': item['package_version'] if item['kind'] == 'historical' else None,
        'firmware_bytes_modified': False, 'hardware_testing': 'not established by archiving',
        'images': [{'name': p.name, 'type': p.name.rsplit('-', 1)[-1].removesuffix('.bin'),
                    'size_bytes': p.stat().st_size, 'sha256': digest(p)} for p in images],
    }
    (output / 'ARCHIVE_RECORD.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    intro = ('这是我补录的历史固件，使用当时成功构建的原始文件，没有重新编译或修改固件内容。\n'
             '版本号取自当时的亚瑟界面包；这次归档不表示补做了实机验收。\n'
             if item['kind'] == 'historical' else
             '这是带作者头像与版本记录的测试候选版，来自对应提交的成功构建。\n')
    body = (f'# {item["title"]}\n\n**by-cookorz**\n\n' + intro + '\n## 这一版的变化\n\n' +
            '\n'.join('- ' + change for change in item['changes']) +
            '\n\n## 下载与刷入\n\n- **U-Boot 刷入：选择 `factory.bin`。**\n'
            '- 系统内升级选择 `sysupgrade.bin`，先确认现有系统的板型与分区布局匹配。\n'
            '- `.bin` 可以直接下载；源码 ZIP / TAR 不属于刷机文件。\n'
            '- `SHA256SUMS` 是原构建提供的固件校验值；`ARCHIVE_RECORD.json` 记录归档来源。\n'
            '- 其余附件是当时的包清单、构建配置与依赖记录。\n'
            '- 历史版本的默认账号、地址和无线设置请以对应提交为准，升级前备份自己的配置。\n'
            '\n## 版本来源\n\n'
            f'- 设备：京东云亚瑟 AX1800 Pro / JDCloud RE-SS-01。\n'
            f'- 原始构建：[Actions #{item["run_number"]}]({run["html_url"]})。\n'
            f'- 源码提交：[`{item["source_commit"][:12]}`](https://github.com/{repository}/commit/{item["source_commit"]})。\n'
            f'- 原始构建时间：`{run["created_at"]}`（UTC）。\n'
            '- 验证范围：原构建成功，归档时重新核对 ZIP 摘要与两份固件的 SHA-256。实机运行情况另行记录。\n'
            '- 本次按测试 / 历史归档发布，保留上游 LibWrt、LuCI、Argon 等项目的来源与许可证。\n')
    if item['version'] is None:
        body = body.replace('版本号取自当时的亚瑟界面包；', '这份初始构建当时没有独立项目版本号，以原 Actions 编号标识；')
    note = working / (item['tag'] + '-notes.md')
    note.write_text(body, encoding='utf-8')
    assets = sorted(p for p in output.iterdir() if p.is_file())
    if len(assets) > 100:
        raise ValueError('Too many release assets')
    print(f'Verified {item["tag"]}: build #{item["run_number"]}, {len(assets)} original records/assets', flush=True)
    return assets, note


def release_for(repository, tag):
    releases = api(f'repos/{repository}/releases?per_page=100')
    matches = [r for r in releases if r['tag_name'] == tag]
    if len(matches) > 1:
        raise ValueError('Ambiguous existing release')
    return matches[0] if matches else None


def verify_tag(repository, tag, commit, required=False):
    ref = api(f'repos/{repository}/git/ref/tags/{tag}', allow_missing=True)
    if ref is None:
        if required:
            raise ValueError('Published tag is missing')
        return
    obj = ref['object']
    for _ in range(5):
        if obj['type'] == 'commit':
            if obj['sha'] != commit:
                raise ValueError('Existing tag points to another source commit')
            return
        if obj['type'] != 'tag':
            break
        obj = api(f'repos/{repository}/git/tags/{obj["sha"]}')['object']
    raise ValueError('Could not resolve release tag')


def verify_asset(repository, tag, path, uploaded):
    if uploaded.get('size') != path.stat().st_size:
        raise ValueError('Release asset size mismatch: ' + path.name)
    expected = 'sha256:' + digest(path)
    if uploaded.get('digest'):
        if uploaded['digest'] != expected:
            raise ValueError('Release asset digest mismatch: ' + path.name)
    else:
        with tempfile.TemporaryDirectory() as name:
            command('release', 'download', tag, '--repo', repository, '--pattern', path.name, '--dir', name)
            if digest(Path(name) / path.name) != expected.removeprefix('sha256:'):
                raise ValueError('Downloaded release asset digest mismatch: ' + path.name)


def publish(item, assets, note, repository):
    tag, commit = item['tag'], item['source_commit']
    verify_tag(repository, tag, commit)
    release = release_for(repository, tag)
    if release is None:
        request = note.parent / (tag + '-create.json')
        request.write_text(json.dumps({'tag_name': tag, 'target_commitish': commit,
            'name': item['title'], 'body': note.read_text(encoding='utf-8'),
            'draft': True, 'prerelease': True, 'make_latest': 'false'}), encoding='utf-8')
        # Use the creation response; the release list can lag behind draft creation.
        release = json.loads(command('api', '--method', 'POST',
            f'repos/{repository}/releases', '--input', str(request)))
    if not release or release['target_commitish'] != commit or release['name'] != item['title']:
        raise ValueError('Existing release does not match the pinned archive: ' + json.dumps(
            {key: release.get(key) for key in ('id','tag_name','target_commitish','name')} if release else None))
    if (release['body'] or '').strip() != note.read_text(encoding='utf-8').strip():
        raise ValueError('Existing release notes differ; refusing to overwrite them')
    uploaded = {a['name']: a for a in api(f'repos/{repository}/releases/{release["id"]}/assets?per_page=100')}
    expected_names = {p.name for p in assets}
    if set(uploaded) - expected_names:
        raise ValueError('Unexpected existing assets; refusing to modify release')
    for path in assets:
        if path.name in uploaded:
            verify_asset(repository, tag, path, uploaded[path.name])
    missing = [p for p in assets if p.name not in uploaded]
    if missing:
        if not release['draft']:
            raise ValueError('Published release incomplete; refusing to modify it')
        command('release', 'upload', tag, *map(str, missing), '--repo', repository)
    uploaded = {a['name']: a for a in api(f'repos/{repository}/releases/{release["id"]}/assets?per_page=100')}
    if set(uploaded) != expected_names:
        raise ValueError('Draft retained: release assets are incomplete')
    for path in assets:
        verify_asset(repository, tag, path, uploaded[path.name])
    if release['draft']:
        command('release', 'edit', tag, '--repo', repository, '--draft=false', '--prerelease=true', '--latest=false')
    verified = api(f'repos/{repository}/releases/{release["id"]}')
    if not verified or verified['draft'] or not verified['prerelease']:
        raise ValueError('Release was not published as a test/archive version')
    verify_tag(repository, tag, commit, required=True)
    print(f'Published and verified: https://github.com/{repository}/releases/tag/{tag}', flush=True)


def main(path):
    plan = read_plan(path)
    repository = plan['repository']
    if os.environ.get('GITHUB_REPOSITORY') != repository:
        raise ValueError('Workflow repository differs from archive plan')
    with tempfile.TemporaryDirectory(prefix='arthur-release-archive-') as name:
        working = Path(name)
        # Verify every original build before creating any public release.
        bundles = [(item, *prepare(item, repository, working)) for item in plan['releases']]
        for item, assets, note in bundles:
            publish(item, assets, note, repository)
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
                    summary.write(f'- [{item["title"]}](https://github.com/{repository}/releases/tag/{item["tag"]}) — build #{item["run_number"]}, original bytes verified\n')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
