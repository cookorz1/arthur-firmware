# Arthur · 京东云亚瑟定制固件

[![Build firmware](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml)

面向 **京东云亚瑟 AX1800 Pro / JDCloud RE-SS-01** 的 OpenWrt 定制固件，基于 **LibWrt 25.12-nss**。集成双频 Wi-Fi、Argon 中文主题、iStore 应用商店、OpenClash、F50 USB 上网，以及 WAN/LAN 端口协商速率面板，方便日常使用和维护。

**当前进度：** 上版已编译并刷机，用户反馈无线网络无法被发现。本次修订初始化顺序、双频就绪检查、信道及加密默认值，并增加 USB 网卡与 USB 总线速率。构建状态以 [最新 Actions 运行](https://github.com/cookorz1/arthur-firmware/actions) 为准；无线广播及连接仍需刷机实测。

## 主要功能

| 功能 | 内容 |
| --- | --- |
| 双频 Wi-Fi | 亚瑟原生 ath11k/IPQ6018 驱动、专用无线校准固件、2.4 GHz / 5 GHz AP、默认 WPA2-PSK |
| Argon 界面 | 默认 Argon 主题，中文 LuCI，集成 Argon 配置插件 |
| iStore | 原版应用商店，按需安装应用；应用依赖仍需与当前固件兼容 |
| OpenClash | 内置插件及构建时的 Mihomo ARM64 稳定核心，导入自己的配置后使用 |
| 随身 WiFi USB 上网 | 按 CDC-ECM / RNDIS / CDC-NCM 驱动识别 USB 共享网络，跨品牌 DHCP 接入，不限 F50 |
| 端口协商速率 | “网络 → 亚瑟网络面板”分别显示 WAN、LAN1、LAN2、LAN3、USB 网卡链路速率，并单独显示 USB 总线连接速率，每 3 秒刷新 |
| USB 上网开关 | 同一页面开启或关闭随身 WiFi 上网，保存并应用后生效；关闭状态在重启、重新插拔后保持 |
| 网络质量检测 | 手动分别检测 WAN / USB 的 IPv4 接入、HTTPS 可达性、两测点延迟与丢包；不伪造蜂窝信号格数或光功率 |
| NSS | 沿用 LibWrt 的 NSS 默认驱动和固件配置；代理流量是否被加速取决于具体工作模式 |

端口速率从物理网口的 sysfs / ethtool 状态读取。未连接的端口显示“未连接”；无法读取实际速率时显示“无法读取”，不会把千兆接口能力当作当前协商速率。该数值也不等于宽带测速结果。

## 常用组件

| 分类 | 已选组件 |
| --- | --- |
| USB 网卡与共享网络 | CDC-ECM、RNDIS、CDC-NCM、RTL8152/RTL8153 系列、ASIX、AX88179，USB 3.0，usb-modeswitch |
| 4G / 5G 模块 | QMI、MBIM、USB 串口 Option/WWAN、CDC-ACM，uqmi、umbim 及 LuCI 协议设置 |
| 存储与文件系统 | USB Storage / UAS、ext4、exFAT、NTFS3、FAT，中文文件名相关 NLS，挂载和分区查看工具 |
| 网络工具 | ethtool-full、iperf3、tcpdump-mini、drill、ip-full |
| 日常管理 | DDNS、网络唤醒 WOL、UPnP 设置、设备流量统计 nlbwmon、TTYD 终端、SFTP、htop、nano |

UPnP 插件默认关闭，按需启用。USB 自动接入根据共享网络驱动识别，不限制厂商；普通 RTL8152/ASIX 网卡以及原始 QMI/MBIM 模块不会被自动设置为 DHCP，可在“网络 → 接口”中手动配置。

## 首次使用

1. 电脑通过网线接入 LAN，打开 **http://192.168.10.1**。
2. 主机名为 `jdy-cookorz`，用户名为 `root`，初始管理密码为 `password`。
3. 打开“网络 → 无线”，查看无线网络及初始密码，再按需要修改名称和密码。
4. 打开“网络 → 亚瑟网络面板”，查看 WAN/LAN/USB 网卡及 USB 总线速率，并设置 USB 上网开关。
5. 随身 WiFi 以 USB 共享网络模式连接后，默认尝试建立 DHCP 接口；如关闭 USB 上网，请在网络面板重新开启并“保存并应用”。为兼容旧版，内部接口名仍保留 `f50`。
6. 在 iStore 中按需安装应用；OpenClash 需导入自己的订阅或配置后开启。

### Wi-Fi 默认设置

| 项目 | 默认值 |
| --- | --- |
| 主机名 | `jdy-cookorz` |
| 管理账号 / 密码 | `root` / `password` |
| 2.4 GHz 名称 / 密码 | `jdy-cookorz2.4G` / `jdy-cookorz2.4G` |
| 5 GHz 名称 / 密码 | `jdy-cookorz5G` / `jdy-cookorz5G` |
| 加密 | WPA2-PSK / AES，可在界面中自行改为 WPA2/WPA3 |
| 2.4 GHz 信道 / 带宽 | 1 / HE20 |
| 5 GHz 信道 / 带宽 | 36（非 DFS）/ HE80 |
| 有线管理地址 | `192.168.10.1` |
| 时区 | 中国上海 |

这些默认值按设备所有者要求设置，适用于全新安装或恢复出厂配置。保留设置升级会继续使用原来的主机名、密码和无线配置。无线初始化等待两个频段配置都出现，最长重试约 60 秒；仅配置未自定义的默认 AP，不覆盖已有自定义网络。首次登录后可自行修改密码、国家及信道。管理密码在构建时生成 SHA-512 哈希，并保留上游其他系统账号。

### USB 速率说明

- **USB 行的链路速率**：读取 USB 网卡的 sysfs / ethtool 驱动报告，驱动未提供时显示“无法读取”。
- **USB 总线连接速率**：读取当前 USB 设备实际枚举速率，例如 `5000 Mbps`（USB 3.x）或 `480 Mbps`（USB 2.0），不以设备标称值代替。
- USB 上网关闭时，仍显示已插入随身 WiFi 的物理连接及总线速率。总线速率不代表 5G 蜂窝速率或互联网测速。

### 网络质量检测与信号强度的区别

打开“网络 → 亚瑟网络面板 → 网络质量检测”，点击“开始检测”。检测是手动触发的短时 IPv4 采样，不持续发送测试流量。

| 检测项 | 说明 |
| --- | --- |
| 上网来源 / IP | 分别查看宽带 WAN 和 USB 随身 WiFi 的接口状态与 IPv4 地址，支持 PPPoE 的实际三层接口 |
| 延迟 / 丢包 | 绑定对应接口，分别向 `223.5.5.5`、`119.29.29.29` 各发送 3 次 ICMP 请求；显示平均延迟和丢包率 |
| HTTPS 可达性 | 绑定对应接口，访问百度、腾讯 HTTPS 首页的响应头，保留证书校验；单个请求最多 4 秒，两来源并行检测 |
| 结果解释 | ICMP 被限制时，HTTPS 成功仍显示外网可达；HTTPS 失败而 ICMP 成功时分别显示，不直接判定断网 |
| 蜂窝 / 光信号 | USB/网线通常不传递 RSRP、RSRQ、SINR、RSSI 或光猫光功率；需要随身 WiFi/光猫开放专用接口，当前显示检测范围说明 |

本功能只检查预设接口 `wan` 和兼容接口 `f50`，使用当前系统路由、DNS 与透明代理策略，不修改路由或防火墙。IPv6-only 接入显示未取得 IPv4，不能据此判断 IPv6 断网。少量采样、测点阻断、DNS 或系统时间异常都可能影响结果；它不是测速或信号强度测量。

### 无线排障

如果干净刷入本版后仍搜不到无线，先等待约一分钟，再通过有线登录终端查看以下输出。配置及信道调整不能代替实际射频测试。

```sh
ubus call network.wireless status
iw dev
logread | grep -Ei 'ath11k|hostapd|wireless|arthur' | tail -n 100
```

### USB 开关的范围

- **开启：** 发现 USB 共享网卡后建立或启用 `f50` DHCP 接口，加入 WAN 防火墙区；已配置的共享设备仍在时优先保留它，第二台设备插入不会抢占。
- **关闭：** 关闭 `f50` 网络接口并禁止其自动启动；随身 WiFi 仍然供电，USB 设备本身不会被断电。
- **重新插拔 / 重启：** 使用已保存的开关状态。
- **其他网络：** 保留有线 WAN 与 LAN 设置；有线 WAN 的路由优先级仍按当前接口配置决定。

## 下载固件

打开 [Actions](https://github.com/cookorz1/arthur-firmware/actions)，选择最新**成功**的构建，在页面底部 **Artifacts** 下载：

```text
Arthur-Enhanced-WiFi-Argon-F50-iStore-运行编号
```

GitHub 下载的是 ZIP，先解压再使用里面的 `.bin` 文件。

| 文件 | 用途 |
| --- | --- |
| `…jdcloud_re-ss-01-squashfs-factory.bin` | 与镜像格式兼容的 U-Boot 固件更新入口 |
| `…jdcloud_re-ss-01-squashfs-sysupgrade.bin` | 与机型、布局及升级脚本匹配的 OpenWrt 系统升级入口 |
| `SHA256SUMS` | 固件文件校验值 |
| `feature-checks.json` | 构建时验证的组件和自定义文件 |
| `resolved.config` / `*.manifest` | 实际生效的构建配置与已安装软件包清单 |

`Arthur-build-logs-*` 是排查构建问题的日志包，不是刷机包。镜像选择应结合实际 U-Boot 和分区布局；不要将 ZIP 改名为 BIN，或强制跳过格式、机型校验。项目不会修改 U-Boot 或自动调整分区。

## 构建与验证

在 GitHub Actions 中手动选择 **Run workflow**，或提交构建相关文件到 `main` 分支。流程依次执行：

1. 测试端口状态读取、USB 关闭/重启/插拔后的状态、重新启用，以及无线初始化和页面渲染。
2. 取得固定提交的 LibWrt、OpenClash、iStore，安装 feeds，生成配置。
3. 按 `required-packages.txt` 核对无线、主题、商店、驱动和网络面板是否确实被选中。
4. 下载 Mihomo ARM64 稳定核心，核对发布摘要（如提供）及 ELF 架构，并记录版本和 SHA-256。
5. 编译固件，检查最终包清单、IPQ6018 运行固件及板级数据、自定义控制脚本、密码哈希、页面和 Argon 资源是否进入固件根目录。
6. 检查 factory/sysupgrade 镜像完整性、6 MiB 内核槽位限制和每个镜像的保守 60 MiB 上限，再上传产物。

构建检查及模拟测试不能代替实机无线、网口 PHY 和 USB 上网测试。主源码及独立插件的固定提交见 `versions.env`；feeds 和 Mihomo 的实际版本会随产物记录。

## 上游项目

- [LibWrt](https://github.com/LiBwrt/LibWrt) · 系统与 NSS 支持
- [ImmortalWrt LuCI](https://github.com/immortalwrt/luci) · 中文界面、Argon 主题与常用插件
- [iStore](https://github.com/istoreos/istore) · 应用商店
- [OpenClash](https://github.com/vernesong/OpenClash) · 代理管理
- [Mihomo](https://github.com/MetaCubeX/mihomo) · ARM64 代理核心

本仓库新增的配置和亚瑟网络面板采用 MIT 许可。固件中各上游组件保留各自的许可证与版权声明。
