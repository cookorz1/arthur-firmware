"""Apply the Arthur skin to the pinned Argon templates without replacing LuCI auth."""
import base64
import pathlib
import re
import shutil
import sys


def integrate(source, project, build_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', build_id):
        raise ValueError('Invalid theme build ID')
    version = (project / 'VERSION').read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?', version):
        raise ValueError('Invalid theme version')
    templates = source / 'feeds/luci/themes/luci-theme-argon/ucode/template/themes/argon'
    link = ('<script>try{document.documentElement.dataset.arthurTheme='
            'localStorage.getItem("arthur-theme") === "dark" ? "dark" : "light"}catch(e){}</script>\n'
            f'<link rel="stylesheet" href="/luci-static/arthur/theme.css?v={build_id}">\n')
    style_dir = source / 'package/custom/arthur/files/www/luci-static/arthur'
    style_dir.mkdir(parents=True, exist_ok=True)
    style = (project / 'package/arthur/files/www/luci-static/arthur/theme.css').read_text(encoding='utf-8')
    (style_dir / 'theme.css').write_text(style.replace('@ARTHUR_BUILD@', build_id), encoding='utf-8')
    # Replace the shared metadata rather than competing with Argon's sized PNG icons.
    metadata = templates / 'head_meta.ut'
    original = metadata.read_text(encoding='utf-8')
    if original.count('<title>') != 1 or original.count(' - LuCI</title>') != 1:
        raise ValueError('Argon metadata title anchor changed')
    head = (project / 'package/arthur/theme/head_meta.ut').read_text(encoding='utf-8')
    metadata.write_text(head.replace('@ARTHUR_BUILD@', build_id), encoding='utf-8')
    avatar = (project / 'package/arthur/files/www/luci-static/arthur/avatar.jpg').read_bytes()
    encoded = base64.b64encode(avatar).decode('ascii')
    # An SVG wrapper embeds the original JPEG bytes, with no external image requests.
    icon = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
            '<image width="64" height="64" preserveAspectRatio="xMidYMid meet" '
            'href="data:image/jpeg;base64,' + encoded + '"/></svg>\n')
    (style_dir / 'favicon.svg').write_text(icon, encoding='utf-8')
    for name in ('header.ut', 'header_login.ut'):
        path = templates / name
        text = path.read_text(encoding='utf-8')
        if text.count('</head>') != 1:
            raise ValueError('Argon head anchor changed: ' + name)
        # Arthur owns the theme switch; avoid a second prefers-color-scheme sheet.
        mode_anchor = "mode = cfg.get_first('argon', 'global', 'mode');"
        if text.count(mode_anchor) != 1:
            raise ValueError('Argon mode anchor changed: ' + name)
        text = text.replace(mode_anchor, "mode = 'light';")
        path.write_text(text.replace('</head>', link + '</head>'), encoding='utf-8')
    path = templates / 'footer.ut'
    text = path.read_text(encoding='utf-8')
    if text.count("L.require('menu-argon')") != 1:
        raise ValueError('Argon menu anchor changed')
    text = text.replace("L.require('menu-argon')", f"L.require('menu-argon'); L.require('arthur-shell-{build_id}')")
    path.write_text(text, encoding='utf-8')
    login = (project / 'package/arthur/theme/sysauth.ut').read_text(encoding='utf-8')
    (templates / 'sysauth.ut').write_text(login.replace('@ARTHUR_VERSION@', version), encoding='utf-8')
    resources = source / 'package/custom/arthur/files/www/luci-static/resources'
    shell = (resources / 'arthur-shell.js').read_text(encoding='utf-8')
    (resources / f'arthur-shell-{build_id}.js').write_text(shell.replace('@ARTHUR_VERSION@', version), encoding='utf-8')


if __name__ == '__main__':
    integrate(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3])

