"""Pin tested feeds, install OpenClash guard hooks and version LuCI view URLs."""
import argparse
import json
import pathlib
import re
import shutil

HOOK = '   /usr/libexec/arthur-performance protect || { LOG_OUT "Arthur NSS protection failed; refusing to start proxy"; return 1; }\n'


def pin_feeds(config, lock):
    seen = set()
    result = []
    for line in config.read_text().splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0] in ('src-git', 'src-git-full') and fields[1] in lock:
            name = fields[1]
            if not re.fullmatch('[a-f0-9]{40}', lock[name]) or name in seen:
                raise ValueError('Invalid or duplicate feed lock: ' + name)
            seen.add(name)
            url = fields[2].split(';')[0].split('^')[0]
            line = ' '.join([fields[0], name, url + '^' + lock[name]])
        result.append(line)
    if seen != set(lock):
        raise ValueError('Missing locked feeds: ' + ', '.join(set(lock) - seen))
    config.write_text('\n'.join(result) + '\n')


def patch_openclash(path):
    text = path.read_text(encoding='utf-8')
    start_anchor = '   if procd_running "openclash" >/dev/null; then'
    stop_anchor = 'stop_service()\n{\n'
    reload_anchor = 'reload_service()\n{\n'
    for anchor in (start_anchor, stop_anchor, reload_anchor):
        if text.count(anchor) != 1:
            raise ValueError('OpenClash hook anchor changed: ' + repr(anchor))
    text = text.replace(start_anchor, HOOK + '\n' + start_anchor, 1)
    text = text.replace(stop_anchor, stop_anchor +
                        '   /usr/libexec/arthur-performance protect || LOG_OUT "Arthur NSS protection failed during stop"\n', 1)
    text = text.replace(reload_anchor, reload_anchor + HOOK, 1)
    path.write_text(text, encoding='utf-8')


def require_guard_package(path):
    text = path.read_text(encoding='utf-8')
    if text.count('DEPENDS:=') != 1:
        raise ValueError('OpenClash dependency anchor changed')
    path.write_text(text.replace('DEPENDS:=', 'DEPENDS:=+luci-app-arthur ', 1), encoding='utf-8')


def version_views(package_files, overlay, build_id):
    if not re.fullmatch('[a-zA-Z0-9_-]{1,64}', build_id):
        raise ValueError('Invalid build ID')
    menu_path = package_files / 'usr/share/luci/menu.d/luci-app-arthur.json'
    menu = json.loads(menu_path.read_text())
    for entry in menu.values():
        action = entry.get('action', {})
        if action.get('type') != 'view':
            continue
        view = action['path']
        source = package_files / 'www/luci-static/resources/view' / (view + '.js')
        destination = source.with_name(source.stem + '-' + build_id + '.js')
        shutil.copyfile(source, destination)
        action['path'] = view + '-' + build_id
    menu_path.write_text(json.dumps(menu, ensure_ascii=False, indent=2) + '\n')
    (overlay / 'etc').mkdir(parents=True, exist_ok=True)
    (overlay / 'etc/arthur-build').write_text(build_id + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['pin', 'integrate'])
    parser.add_argument('source', type=pathlib.Path)
    parser.add_argument('argument')
    args = parser.parse_args()
    if args.action == 'pin':
        pin_feeds(args.source / 'feeds.conf.default', json.loads(pathlib.Path(args.argument).read_text()))
    else:
        patch_openclash(args.source / 'package/custom/luci-app-openclash/root/etc/init.d/openclash')
        require_guard_package(args.source / 'package/custom/luci-app-openclash/Makefile')
        version_views(args.source / 'package/custom/arthur/files', args.source / 'files', args.argument)
