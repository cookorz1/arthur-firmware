<div align="center">

<img src="package/arthur/files/www/luci-static/arthur/avatar.jpg" width="96" height="96" alt="cookorz 的头像">

# jdy-cookorz

**京东云亚瑟 AX1800 Pro 定制固件 · by-cookorz**

USB 随身 WiFi 上网 · 中文 Argon 界面 · iStore · OpenClash · 网络与内存面板

[![构建状态](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml)
[![候选版本](https://img.shields.io/badge/version-1.5.0--rc.4-orange)](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.4)

[下载最新版](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.4) · [全部版本](https://github.com/cookorz1/arthur-firmware/releases) · [更新日志](CHANGELOG.md) · [使用与排查](docs/USAGE.md) · [自行编译](docs/BUILDING.md)

</div>

## 我为什么做这份固件

我是 cookorz。我平时用京东云亚瑟接随身 WiFi 上网，这份固件最初就是为自己的使用习惯整理的：插上 USB 能共享网络，常用插件方便安装，打开管理页面就能看清端口、网速和内存状态。

系统基于 LibWrt，界面以 Argon 为基础。我把双频 Wi-Fi、iStore、OpenClash、网络检测和加速设置放到一套中文界面里，保留雪山登录页、深浅色切换和手机布局。Logo、登录页头像和浏览器标签页图标都用我的头像，统一署名 **by-cookorz**。

我会把每一版的改动、构建来源和验证范围写清楚。发现问题可以带上版本号反馈，旧版下载也会保留，方便比较和回退。

## 最新版本与下载

目前最新测试候选版是 **[v1.5.0-rc.4](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.4)**，对应 [Actions #16](https://github.com/cookorz1/arthur-firmware/actions/runs/39605685842)，源码提交 [`0a712e63c0d9`](https://github.com/cookorz1/arthur-firmware/commit/0a712e63c0d9db085f64419a31ed7a83fca6aad5)。

| 下载 | 用途 |
| --- | --- |
| **[factory.bin · U-Boot 刷入](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.4/jdy-cookorz-arthur-v1.5.0-rc.4-0a712e63c0d9-factory.bin)** | 使用兼容本镜像格式的 U-Boot 刷机 |
| **[sysupgrade.bin · 系统内升级](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.4/jdy-cookorz-arthur-v1.5.0-rc.4-0a712e63c0d9-sysupgrade.bin)** | 从板型和分区布局匹配的系统升级 |
| [SHA256SUMS](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.4/SHA256SUMS) | 核对两份固件是否下载完整 |
| [版本来源记录](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.4/FIRMWARE_VERSION.json) | 版本、原构建、源码、依赖和镜像摘要 |

**用 U-Boot 就下载 factory.bin。** Releases 中的 `.bin` 可直接下载；GitHub 自动附带的 Source code ZIP / TAR 是源码，不能刷机。Actions 的 Artifacts 是 ZIP，下载后需要先解压。

此版已通过行为测试、浏览器界面检查和编译校验，仍标为 **Pre-release**。此前的手动调试已验证软件分载在这台设备上有收益；新镜像的启动、热插拔和完整共存表现还需刷入后验收，不把“构建成功”当作“所有功能已经实测稳定”。

### rc.4 这次改了什么

- “网络 → 加速与内存”新增 **软件流量分载**，可以和原来的 NSS 自动兼容模式、关闭模式切换。
- 软件模式先清退并卸载 ECM；切回 NSS 或启动 OpenClash 前撤销软件规则，两种转发加速互斥。
- OpenClash 开启、核心仍运行或 SQM/QoS 工作时保留兼容保护；条件解除后恢复所选模式，后台保护服务保持运行。
- 首页和性能页显示所选模式、实际规则及错误原因；保留旧设置，不自动替用户切换。
- 包含 rc.3 的标签页标题和头像图标修复。完整记录见 [更新日志](CHANGELOG.md)。

## 适用设备

| 项目 | 配置 |
| --- | --- |
| 设备 | **京东云亚瑟 AX1800 Pro / JDCloud RE-SS-01** |
| 板型 | `jdcloud,re-ss-01` |
| 平台 | `qualcommax/ipq60xx` · IPQ6018 |
| 系统来源 | LibWrt，主源码与插件版本见 [versions.env](versions.env) |
| 依赖版本 | 固定 feeds 提交，见 [feeds.lock.json](feeds.lock.json) |
| 维护者 | **by-cookorz** |

刷入前确认自己的设备板型、U-Boot 和分区布局，备份原配置。本项目不更改 U-Boot 或重新分区。

## 常用功能

| 功能 | 实际用途 |
| --- | --- |
| 定制首页 | WAN / USB 实时流量、CPU、可用内存、存储、端口状态、设备列表与应用入口 |
| 中文 Argon 界面 | 统一登录页、作者头像、版本号、深浅色切换及手机布局 |
| 双频 Wi-Fi | 亚瑟原生 ath11k 驱动与板级固件，2.4 GHz / 5 GHz AP |
| iStore / OpenClash | 应用商店、OpenClash，以及构建时记录版本的 Mihomo ARM64 核心 |
| USB 网络共享 | CDC-ECM / RNDIS / CDC-NCM 随身 WiFi 的 DHCP 接入，开关状态重启和重新插拔后保留 |
| 端口与 USB 状态 | WAN、LAN1–LAN3 链路速率，USB 网卡驱动报告速率，单独显示 USB 总线枚举速率 |
| 网络质量检测 | 手动检测 WAN / USB 的 IPv4、延迟、丢包和 HTTPS 可达性 |
| 转发加速 | NSS / 软件流量分载 / 关闭三种选择，OpenClash 与 SQM/QoS 兼容保护 |
| 内存管理 | 128 MiB ZRAM、MemAvailable、代理内存参考值和手动缓存回收 |
| 常用工具与驱动 | USB 网卡、存储及常见文件系统，QMI / MBIM，DDNS、WOL、流量统计、TTYD、SFTP、iperf3、ethtool 等 |

USB 网卡速率、USB 总线速率、蜂窝网络速率是不同的数据，不能相互替代。当前网络检测不读取 RSRP / SINR 或光猫光功率；USB 上网开关只控制网络接入，关闭后随身 WiFi 仍会供电。

## 第一次开机

电脑先通过网线接入 LAN，打开 **http://192.168.10.1**。

| 项目 | 全新安装的初始值 |
| --- | --- |
| 主机名 | `jdy-cookorz` |
| 管理账号 / 密码 | `root` / `password` |
| 2.4 GHz 名称 / 密码 | `jdy-cookorz2.4G` / `jdy-cookorz2.4G` |
| 5 GHz 名称 / 密码 | `jdy-cookorz5G` / `jdy-cookorz5G` |
| 无线模式 | WPA2-PSK / AES；2.4 GHz HE20，5 GHz HE80 |
| 时区 | 中国上海 |

这些是全新安装或恢复出厂设置的初始值，保留配置升级会沿用原设置。无线初始化可能需要约一分钟，首次登录后请自行修改管理和无线密码。

1. 随身 WiFi 先开启 USB 网络共享，再接入亚瑟。
2. 在 **网络 → 亚瑟网络面板** 查看 USB 接入、WAN/LAN 状态，按需运行网络质量检测。
3. USB 用户可到 **网络 → 加速与内存 → 转发加速模式** 选择软件流量分载，保存并应用后对比实际效果。
4. OpenClash 导入自己的订阅或配置后启用；其他应用在 iStore 按需安装。

OpenClash 启用或核心仍运行时，两种转发分载都会暂停；测速流量是否走代理节点，取决于实际规则。BBR 影响路由器本机及代理出口的内核 TCP 连接，不改变终端设备的拥塞算法。ZRAM 是压缩交换，手动回收只释放可回收缓存，不能清掉程序正在使用的内存。

## 版本记录

| 版本 | 主要变化 | 下载 |
| --- | --- | --- |
| **1.5.0-rc.4** | USB 软件分载与 OpenClash 保护、实际加速状态 | [最新测试候选版](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.4) |
| 1.5.0-rc.3 | `jdy-cookorz` 标签页标题与头像图标修复 | [Release](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.3) |
| 1.5.0-rc.2 | 作者头像、署名、统一版本与来源记录 | [Release](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.2) |
| 1.0.0～1.4.0 / build-4 | Wi-Fi、USB、网络检测、NSS、内存及定制首页的开发历程 | [历史版本与原构建](.github/RELEASE_ARCHIVE.md) |

我用 `VERSION` 管理源码版本，用 [CHANGELOG.md](CHANGELOG.md) 记录每次变化；Releases 固定保存对应提交的镜像、SHA-256 和原构建记录。已发布的版本不替换附件、不移动标签，需要修正就发新版本。没有成功生成镜像的构建保留在 Actions，不创建空的 Release。

[版本与发布流程](docs/VERSIONING.md) · [使用与排查](docs/USAGE.md) · [自行编译](docs/BUILDING.md)

## 问题反馈

到 [Issues](https://github.com/cookorz1/arthur-firmware/issues) 写明机型、固件版本、刷入方式、是否保留配置及复现步骤。网络问题请补充 USB / WAN 类型、OpenClash 模式和转发加速设置，日志里去掉订阅地址、节点密码等私密信息。

SSH 中可以确认自己刷入的版本与源码：

```sh
cat /etc/arthur-version
cat /etc/arthur-build
```

## 致谢与许可

感谢 [LibWrt](https://github.com/LiBwrt/LibWrt)、[ImmortalWrt LuCI](https://github.com/immortalwrt/luci)、[Argon](https://github.com/jerrykuku/luci-theme-argon)、[iStore](https://github.com/istoreos/istore)、[OpenClash](https://github.com/vernesong/OpenClash) 和 [Mihomo](https://github.com/MetaCubeX/mihomo) 等项目的维护者。

我维护这里的亚瑟适配配置、网络面板和定制界面。仓库自定义代码按 [MIT](LICENSE) 许可使用，各上游软件继续遵循自己的许可证。头像仅用于本项目的作者标识，不属于 MIT 代码授权范围。
