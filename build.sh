#!/usr/bin/env bash
set -Eeuo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$TASK_ROOT"
source versions.env
BUILD_ID="${GITHUB_SHA:-local-$(date -u +%Y%m%d%H%M%S)}"
python3 "$TASK_ROOT/scripts/firmware_release.py" check "$TASK_ROOT"
mkdir -p logs output
exec > >(tee -a logs/build.log) 2>&1
trap 'echo "Build failed at line $LINENO. Inspect logs/build.log."' ERR
checkout_commit() {
    local url="$1" commit="$2" destination="$3"
    git init "$destination"
    git -C "$destination" remote add origin "$url"
    git -C "$destination" fetch --depth=1 origin "$commit"
    git -C "$destination" checkout --detach FETCH_HEAD
    test "$(git -C "$destination" rev-parse HEAD)" = "$commit"
}
if [ "${BUILD_ONLY:-0}" != 1 ]; then
test ! -e openwrt || { echo 'Use a fresh directory for this build.'; exit 1; }
checkout_commit "$SOURCE_URL" "$SOURCE_COMMIT" openwrt
checkout_commit "$OPENCLASH_URL" "$OPENCLASH_COMMIT" openclash-src
checkout_commit "$ISTORE_URL" "$ISTORE_COMMIT" istore-src
cd openwrt
python3 "$TASK_ROOT/scripts/integrate_performance.py" pin . "$TASK_ROOT/feeds.lock.json"
printf '\nsrc-link istore %s\n' "$TASK_ROOT/istore-src" >> feeds.conf.default
./scripts/feeds update -a
./scripts/feeds install -a
./scripts/feeds install -f -d y -p istore luci-app-store luci-lib-taskd luci-lib-xterm taskd
mkdir -p package/custom
# Replace a feed's OpenClash package if present, avoiding duplicate definitions.
find package/feeds -type l -name luci-app-openclash -delete
cp -a "$TASK_ROOT/openclash-src/luci-app-openclash" package/custom/
cp -a "$TASK_ROOT/package/arthur" package/custom/arthur
cp "$TASK_ROOT/config.seed" .config
make defconfig
cp .config "$TASK_ROOT/logs/resolved.config"
cp tmp/.packageinfo "$TASK_ROOT/logs/packageinfo.txt"
cp tmp/.config-package.in "$TASK_ROOT/logs/config-package.in"
required=(
  TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-ss-01
  ATH11K_NSS_SUPPORT ATH11K_MEM_PROFILE_512M NSS_FIRMWARE_VERSION_11_4
)
while IFS= read -r package_name; do
    [ -z "$package_name" ] || required+=("PACKAGE_$package_name")
done < "$TASK_ROOT/required-packages.txt"
for symbol in "${required[@]}"; do
    grep -Fqx "CONFIG_${symbol}=y" .config || {
        echo "Required selection missing after defconfig: CONFIG_${symbol}"
        grep -n -A30 -B2 'PACKAGE_luci-app-store' tmp/.config-package.in || true
        grep -n -A25 -B2 'PACKAGE_luci-lib-taskd' tmp/.config-package.in || true
        grep -n -A25 -B2 'PACKAGE_taskd' tmp/.config-package.in || true
        grep -E 'store|taskd|xterm|libuci-lua|mount-utils|script-utils|coreutils|liblua' .config || true
        exit 1;
    }
done
cp -a "$TASK_ROOT/files" .
python3 "$TASK_ROOT/scripts/firmware_release.py" stamp "$TASK_ROOT" . "$BUILD_ID"
python3 "$TASK_ROOT/scripts/integrate_performance.py" integrate . "$BUILD_ID"
python3 "$TASK_ROOT/scripts/integrate_theme.py" . "$TASK_ROOT" "$BUILD_ID"
sh -n package/custom/luci-app-openclash/root/etc/init.d/openclash
# Initialise root/password only in the clean image; retained sysupgrade settings win.
python3 "$TASK_ROOT/scripts/prepare_defaults.py" package/base-files/files/etc/shadow files/etc/shadow
# Apply our LuCI language/theme after the upstream 99-default-settings scripts.
mv files/etc/uci-defaults/99-arthur-custom files/etc/uci-defaults/zz-arthur-custom
find files/etc/uci-defaults files/etc/init.d -type f -exec chmod 0755 {} +
mkdir -p files/etc/openclash/core
# Embed the stable upstream arm64 Mihomo core, recording its version and hash.
python3 - "$TASK_ROOT/output/core-version.json" <<'PY'
import gzip, hashlib, json, os, re, sys, urllib.request
def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'arthur-firmware-build'})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()
release = json.loads(fetch('https://api.github.com/repos/MetaCubeX/mihomo/releases/latest'))
assets = [a for a in release['assets'] if re.fullmatch(r'mihomo-linux-arm64-v[0-9.]+\.gz', a['name'])]
if len(assets) != 1:
    raise SystemExit('Expected exactly one stable Mihomo linux-arm64 .gz asset')
asset = assets[0]
archive = fetch(asset['browser_download_url'])
digest = hashlib.sha256(archive).hexdigest()
if asset.get('digest') and asset['digest'] != 'sha256:' + digest:
    raise SystemExit('Mihomo release asset digest mismatch')
core = gzip.decompress(archive)
if core[:4] != b'\x7fELF' or int.from_bytes(core[18:20], 'little') != 183:
    raise SystemExit('Mihomo asset is not an AArch64 ELF executable')
path = 'files/etc/openclash/core/clash_meta'
with open(path, 'wb') as stream:
    stream.write(core)
os.chmod(path, 0o755)
with open(sys.argv[1], 'w') as stream:
    json.dump({'tag': release['tag_name'], 'asset': asset['name'], 'sha256_gzip': digest,
               'sha256_core': hashlib.sha256(core).hexdigest()}, stream, indent=2)
PY
cp .config "$TASK_ROOT/output/resolved.config"
./scripts/diffconfig.sh > "$TASK_ROOT/output/config.diff"
cp feeds.conf.default "$TASK_ROOT/output/feeds.conf.default"
for feed in feeds/*; do
    [ -d "$feed/.git" ] || [ -f "$feed/.git" ] || continue
    printf '%s %s\n' "$feed" "$(git -C "$feed" rev-parse HEAD)"
done > "$TASK_ROOT/output/feed-revisions.txt"
cp "$TASK_ROOT/versions.env" "$TASK_ROOT/output/versions.env"
cp "$TASK_ROOT/feeds.lock.json" "$TASK_ROOT/output/feeds.lock.json"
cp "$TASK_ROOT/required-packages.txt" "$TASK_ROOT/output/required-packages.txt"
fi
[ "${PREPARE_ONLY:-0}" != 1 ] || { echo 'Preparation and required-package checks completed.'; exit 0; }
cd "$TASK_ROOT/openwrt"
make download -j8
make -j"${BUILD_JOBS:-$(nproc)}" || make -j1 V=s
python3 - "$TASK_ROOT/output" <<'PY'
import hashlib, json, pathlib, shutil, sys, tarfile
target = pathlib.Path('bin/targets/qualcommax/ipq60xx')
output = pathlib.Path(sys.argv[1])
images = sorted(p for p in target.glob('*jdcloud_re-ss-01*') if p.name.endswith(('-factory.bin', '-sysupgrade.bin')))
if not any(p.name.endswith('-factory.bin') for p in images) or not any(p.name.endswith('-sysupgrade.bin') for p in images):
    raise SystemExit('Both factory and sysupgrade images are required; no firmware published')
for image in images:
    if image.name.endswith('-sysupgrade.bin'):
        with tarfile.open(image, 'r:') as archive:
            kernels = [member for member in archive.getmembers() if member.name.endswith('/kernel') and member.isfile()]
            if len(kernels) != 1 or kernels[0].size > 6144 * 1024:
                raise SystemExit('Missing or oversized kernel for the upstream 6144 KiB kernel slot')
if any(p.stat().st_size > 60 * 1024 * 1024 for p in images):
    raise SystemExit('Firmware exceeds the conservative 60 MiB limit; review partition layout before increasing it')
manifests = list(target.glob('*.manifest'))
if not manifests:
    raise SystemExit('Package manifest missing')
manifest_text = '\n'.join(p.read_text() for p in manifests)
for package in (output / 'required-packages.txt').read_text().splitlines():
    if not package:
        continue
    if not any(line.startswith(package + ' - ') for line in manifest_text.splitlines()):
        raise SystemExit('Required package missing from output manifest: ' + package)
roots = list(pathlib.Path('build_dir').glob('target-*/root-qualcommax'))
if len(roots) != 1:
    raise SystemExit('Expected one assembled firmware root for custom feature verification')
root = roots[0]
required_files = [
    'usr/libexec/rpcd/arthur', 'usr/libexec/arthur-usb', 'usr/libexec/arthur-health', 'etc/init.d/arthur',
    'usr/libexec/arthur-performance', 'usr/libexec/arthur-performance-watch',
    'usr/libexec/arthur-dashboard',
    'etc/init.d/arthur-performance', 'etc/init.d/qca-nss-ecm',
    'etc/uci-defaults/91-arthur-performance', 'etc/arthur-build',
    'etc/arthur-version', 'etc/arthur-release.json',
    'etc/hotplug.d/net/90-f50', 'etc/config/arthur',
    'etc/uci-defaults/99-arthur-wireless', 'etc/uci-defaults/zz-arthur-custom',
    'www/luci-static/resources/view/arthur/network.js',
    'www/luci-static/resources/view/arthur/performance.js',
    'www/luci-static/resources/view/arthur/dashboard.js',
    'www/luci-static/arthur/theme.css', 'www/luci-static/arthur/mountain.png',
    'www/luci-static/arthur/logo.svg',
    'usr/share/luci/menu.d/luci-app-arthur.json',
    'usr/share/rpcd/acl.d/luci-app-arthur.json'
]
for relative in required_files:
    if not (root / relative).is_file():
        raise SystemExit('Custom feature missing from firmware root: ' + relative)
if not (root / 'www/luci-static/argon').is_dir():
    raise SystemExit('Argon theme assets missing from firmware root')
templates = root / 'usr/share/ucode/luci/template/themes/argon'
for name in ('header.ut', 'header_login.ut'):
    if '/luci-static/arthur/theme.css?v=' not in (templates / name).read_text():
        raise SystemExit('Arthur skin missing from ' + name)
login = (templates / 'sysauth.ut').read_text()
if 'arthur-login' not in login or 'luci_username' not in login or 'luci_password' not in login:
    raise SystemExit('Arthur login template or LuCI authentication form missing')
if not list((root / 'www/luci-static/resources').glob('arthur-shell-*.js')):
    raise SystemExit('Versioned Arthur navigation shell missing')
if '@ARTHUR_VERSION@' in login or 'by-cookorz' not in login:
    raise SystemExit('Login version/author stamping missing')
version = (root / 'etc/arthur-version').read_text().strip()
if version not in login or json.loads((root/'etc/arthur-release.json').read_text())['version'] != version:
    raise SystemExit('UI version differs from firmware version')
menu = json.loads((root / 'usr/share/luci/menu.d/luci-app-arthur.json').read_text())
for entry in menu.values():
    view = entry.get('action', {}).get('path', '')
    if view and not (root / 'www/luci-static/resources/view' / (view + '.js')).is_file():
        raise SystemExit('Versioned LuCI view missing: ' + view)
if (root / 'etc/init.d/openclash').read_text().count('/usr/libexec/arthur-performance protect') != 3:
    raise SystemExit('OpenClash lifecycle guard hooks missing from firmware')
if 'nf_conntrack' in (root / 'etc/init.d/qca-nss-ecm').read_text():
    raise SystemExit('Unsafe upstream ECM startup script was not replaced')
for module in ('tcp_bbr', 'sch_fq', 'zram'):
    if not list(root.glob('lib/modules/*/' + module + '.ko*')):
        raise SystemExit('Required performance kernel module missing: ' + module)
shadow = (root / 'etc/shadow').read_text()
root_entries = [line.split(':') for line in shadow.splitlines() if line.startswith('root:')]
if len(root_entries) != 1 or not root_entries[0][1].startswith('$6$'):
    raise SystemExit('Clean-image root password hash missing')
firmware_files = [
    'lib/firmware/ath11k/IPQ6018/hw1.0/board-2.bin',
    'lib/firmware/IPQ6018/q6_fw.mdt',
    'lib/firmware/IPQ6018/m3_fw.mdt',
    'lib/firmware/IPQ6018/q6_fw.b03',
    'lib/firmware/IPQ6018/m3_fw.b02'
]
for relative in firmware_files:
    if not (root / relative).is_file():
        raise SystemExit('Ath11k runtime firmware file missing: ' + relative)
(output / 'feature-checks.json').write_text(json.dumps({
    'custom_files': required_files, 'argon_assets': True,
    'ath11k_firmware_files': firmware_files, 'root_password_sha512': True,
    'openclash_guard_hooks': 3, 'versioned_views': True,
    'performance_modules': ['tcp_bbr', 'sch_fq', 'zram'],
    'required_packages': (output / 'required-packages.txt').read_text().splitlines(),
    'hardware_testing': 'pending for enhanced features'
}, indent=2))
for source in [*images, *manifests, *target.glob('*.buildinfo'), *target.glob('profiles.json')]:
    shutil.copy2(source, output / source.name)
with (output / 'SHA256SUMS').open('w') as stream:
    for image in images:
        stream.write(hashlib.sha256(image.read_bytes()).hexdigest() + '  ' + image.name + '\n')
(output / 'BUILD_STATUS.txt').write_text('Compiled successfully. Hardware boot, partition compatibility, USB uplink and application behavior still require device testing.\n')
PY
python3 "$TASK_ROOT/scripts/firmware_release.py" prepare "$TASK_ROOT" "$TASK_ROOT/output" "$BUILD_ID"
echo 'Build complete. Artifacts are in output/; confirm the device partition layout before flashing.'

