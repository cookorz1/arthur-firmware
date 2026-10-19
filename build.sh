#!/usr/bin/env bash
set -Eeuo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$TASK_ROOT"
source versions.env
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
printf '\nsrc-link istore %s\n' "$TASK_ROOT/istore-src" >> feeds.conf.default
./scripts/feeds update -a
./scripts/feeds install -a
./scripts/feeds install -f -p istore luci-app-store luci-lib-taskd luci-lib-xterm taskd
mkdir -p package/custom
# Replace a feed's OpenClash package if present, avoiding duplicate definitions.
find package/feeds -type l -name luci-app-openclash -delete
cp -a "$TASK_ROOT/openclash-src/luci-app-openclash" package/custom/
cp "$TASK_ROOT/config.seed" .config
make defconfig
cp .config "$TASK_ROOT/logs/resolved.config"
cp tmp/.packageinfo "$TASK_ROOT/logs/packageinfo.txt"
cp tmp/.config-package.in "$TASK_ROOT/logs/config-package.in"
required=(
  TARGET_qualcommax_ipq60xx_DEVICE_jdcloud_re-ss-01
  PACKAGE_luci-app-openclash PACKAGE_luci-app-store PACKAGE_luci-compat
  PACKAGE_kmod-usb-net-cdc-ether PACKAGE_kmod-usb-net-rndis
  PACKAGE_kmod-usb-net-cdc-ncm PACKAGE_usb-modeswitch
  PACKAGE_dnsmasq-full PACKAGE_kmod-nft-tproxy
)
for symbol in "${required[@]}"; do
    grep -Fqx "CONFIG_${symbol}=y" .config || {
        echo "Required selection missing after defconfig: CONFIG_${symbol}"; exit 1;
    }
done
cp -a "$TASK_ROOT/files" .
chmod 0755 files/etc/uci-defaults/99-arthur-custom files/etc/hotplug.d/net/90-f50
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
fi
[ "${PREPARE_ONLY:-0}" != 1 ] || { echo 'Preparation and required-package checks completed.'; exit 0; }
cd "$TASK_ROOT/openwrt"
make download -j8
make -j"${BUILD_JOBS:-$(nproc)}" || make -j1 V=s
python3 - "$TASK_ROOT/output" <<'PY'
import hashlib, pathlib, shutil, sys, tarfile
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
for package in ['luci-app-openclash', 'luci-app-store', 'kmod-usb-net-cdc-ether', 'kmod-usb-net-rndis', 'kmod-usb-net-cdc-ncm']:
    if not any(line.startswith(package + ' - ') for line in manifest_text.splitlines()):
        raise SystemExit('Required package missing from output manifest: ' + package)
for source in [*images, *manifests, *target.glob('*.buildinfo'), *target.glob('profiles.json')]:
    shutil.copy2(source, output / source.name)
with (output / 'SHA256SUMS').open('w') as stream:
    for image in images:
        stream.write(hashlib.sha256(image.read_bytes()).hexdigest() + '  ' + image.name + '\n')
(output / 'BUILD_STATUS.txt').write_text('Compiled successfully. Hardware boot, partition compatibility, USB uplink and application behavior still require device testing.\n')
PY
echo 'Build complete. Artifacts are in output/; confirm the device partition layout before flashing.'
