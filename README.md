<div align="center">

<img src="package/arthur/files/www/luci-static/arthur/avatar.jpg" width="96" height="96" alt="cookorz 作者标志">

# jdy-cookorz

**京东云亚瑟 AX1800 Pro 定制固件 · by-cookorz**

USB 随身 WiFi 上网 · 双频 Wi-Fi · 中文 Argon · iStore · OpenClash

[![构建状态](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml)
[![源码版本](https://img.shields.io/badge/source-1.5.0--rc.5-blue)](VERSION)
[![已发布候选版](https://img.shields.io/badge/release-1.5.0--rc.5-orange)](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.5)

[固件下载](https://github.com/cookorz1/arthur-firmware/releases) · [更新日志](CHANGELOG.md) · [源码与构建](#源码与构建) · [使用与排查](docs/USAGE.md)

</div>

## 项目简介

**jdy-cookorz** 是面向京东云亚瑟 **AX1800 Pro / JDCloud RE-SS-01** 的定制路由固件，基于 LibWrt，由 **cookorz** 维护。项目围绕 USB 随身 WiFi 网络共享、家庭有线与无线接入、应用管理和网络状态查看进行适配。

**rc.5 重点优化 USB 随身 WiFi 上网后，经亚瑟 Wi-Fi 共享的转发体验**，默认开启软件流量分载与 USB 多核分流。使用者提供的三轮对照中，新固件平均为 **425.76 Mbps**，旧固件平均为 **374.30 Mbps**，提升约 **13.7%**，新固件最高为 **465.70 Mbps**。完整采样与测试范围见 [实测记录](docs/PERFORMANCE.md)。

系统集成中文 Argon、双频 Wi-Fi、iStore 和 OpenClash。定制首页集中展示 WAN / USB 流量、端口链路速率、CPU、内存与设备状态；网络面板提供 USB 上网开关和网络质量检测，加速页面统一管理软件流量分载、NSS、USB 多核分流与内存功能。

登录页、管理侧栏和浏览器图标统一使用作者头像与 **by-cookorz** 标识，支持深浅色切换和手机布局。定制代码、构建配置及发布流程公开，每个发布版本保留源码提交、构建记录与镜像校验文件。

## 版本状态与下载

| 状态 | 版本 | 来源 |
| --- | --- | --- |
| 最新已发布候选版 | **1.5.0-rc.5** | [Release](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.5) · [Actions #17](https://github.com/cookorz1/arthur-firmware/actions/runs/39768121777) |
| 上一候选版 | **1.5.0-rc.4** | [Release](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.4) · [Actions #16](https://github.com/cookorz1/arthur-firmware/actions/runs/39605685842) |
| 历史版本 | build-4 ～ 1.5.0-rc.3 | [全部 Releases](https://github.com/cookorz1/arthur-firmware/releases) · [历史构建来源](.github/RELEASE_ARCHIVE.md) |

**rc.5 已构建成功并发布，现可直接下载。** 对应源码提交 [`01e43e4a7ffa`](https://github.com/cookorz1/arthur-firmware/tree/01e43e4a7ffaf9cd28389c317015b39444bd0047)，已通过行为测试、界面检查、编译与附件校验，并收到 USB 共享经 Wi-Fi 使用的实测反馈；继续保留 Pre-release 标记。

### rc.5 固件下载

| 文件 | 用途 |
| --- | --- |
| **[factory.bin](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.5/jdy-cookorz-arthur-v1.5.0-rc.5-01e43e4a7ffa-factory.bin)** | 通过兼容本镜像格式及分区布局的 U-Boot 刷入 |
| **[sysupgrade.bin](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.5/jdy-cookorz-arthur-v1.5.0-rc.5-01e43e4a7ffa-sysupgrade.bin)** | 从板型和分区布局匹配的系统内升级 |
| [SHA256SUMS](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.5/SHA256SUMS) | 下载完整性校验 |
| [FIRMWARE_VERSION.json](https://github.com/cookorz1/arthur-firmware/releases/download/v1.5.0-rc.5/FIRMWARE_VERSION.json) | 镜像名称、大小、SHA-256、源码提交及原始构建记录 |

使用 U-Boot 刷机时选择 **factory.bin**。GitHub 自动附带的 **Source code ZIP / TAR 是源码包**；刷机使用 Release 附件中的 `.bin`。Actions 的 Artifacts 为 ZIP，需要先解压。

### rc.5 更新重点

- **USB 多核分流默认开启**：四核亚瑟使用在线 CPU0、CPU1、CPU3，自动识别 USB 共享网卡，开机和重插后恢复设置。
- **OpenClash 运行时保留 RPS**：接收处理分流与转发分载独立控制，页面显示接口、队列掩码及实际状态。
- **软件流量分载作为全新安装默认值**：保留配置升级沿用原转发模式；USB 多核分流提供独立开关。
- **保留代理兼容保护**：OpenClash 配置启用或核心仍运行时，NSS 和软件转发分载暂停，条件解除后恢复所选模式。
- **新版本自动发布**：成功构建的新版本经来源与附件校验后发布；已有 Release 和镜像保持原样。

rc.5 已收到 USB 上网经 Wi-Fi 转发的测速反馈，三次完整采样的平均值较旧固件提升约 13.7%；各次仍有波动。该结果反映本次设备与网络条件下的整体表现，不能单独归因于 RPS，也不能作为代理节点测速结果。长时间稳定性、USB 重连恢复和 OpenClash 实际吞吐仍待补充验收。完整数据见 [实测记录](docs/PERFORMANCE.md)，功能变化见 [CHANGELOG.md](CHANGELOG.md)。

## 设备与刷入条件

| 项目 | 说明 |
| --- | --- |
| 设备型号 | **京东云亚瑟 AX1800 Pro / JDCloud RE-SS-01** |
| 板型标识 | `jdcloud,re-ss-01` |
| 目标平台 | `qualcommax/ipq60xx` |
| 固件基础 | LibWrt；主源码与插件提交见 [versions.env](versions.env) |
| feeds 版本 | 按 [feeds.lock.json](feeds.lock.json) 固定提交 |
| 维护与定制 | **by-cookorz** |

刷入前需确认板型、U-Boot、镜像格式及分区布局，并备份原配置。当前已验证设备使用 **6 MiB 内核槽和 2 GiB rootfs**；2 GiB 并非统一的强制要求，原厂分区尚未完成直接刷入验证。本项目不会修改 U-Boot 或自动重新分区。

## 主要功能

| 功能 | 内容 |
| --- | --- |
| 定制管理首页 | WAN / USB 实时流量、CPU、可用内存、存储、端口状态、设备列表与应用入口 |
| 中文 Argon | 雪山登录页、统一作者标识、深浅色切换与手机布局 |
| 双频 Wi-Fi | 亚瑟原生 ath11k 驱动及板级固件，2.4 GHz / 5 GHz AP |
| 应用与代理 | iStore、OpenClash，以及构建时记录版本与摘要的 Mihomo ARM64 核心 |
| USB 网络共享 | CDC-ECM / RNDIS / CDC-NCM 随身 WiFi DHCP 接入；开关状态在重启和重插后保留 |
| 端口状态 | WAN、LAN1–LAN3 链路速率、USB 网卡驱动报告速率与 USB 总线枚举速率 |
| 网络质量检测 | 手动检测 WAN / USB 的 IPv4、延迟、丢包和 HTTPS 可达性 |
| 转发与多核设置 | NSS、软件流量分载、USB RPS，以及 OpenClash / SQM 兼容保护 |
| 内存管理 | 128 MiB ZRAM、可用内存、代理内存参考值与手动缓存回收 |
| 常用驱动与工具 | USB 网卡、存储、常见文件系统、QMI / MBIM、DDNS、WOL、流量统计、TTYD、SFTP、iperf3、ethtool 等 |

USB 网卡报告速率、USB 总线速率和蜂窝网络测速分别展示。网络质量检测目前不读取 RSRP / SINR 或光猫光功率；USB 上网开关控制网络接入，关闭后随身 WiFi 仍会供电。

## 默认设置与首次使用

电脑通过网线连接 LAN，打开 **[http://192.168.10.1](http://192.168.10.1)**。

| 项目 | 全新安装的初始值 |
| --- | --- |
| 主机名 | `jdy-cookorz` |
| 管理账号 / 密码 | `root` / `password` |
| 2.4 GHz 名称 / 密码 | `jdy-cookorz2.4G` / `jdy-cookorz2.4G` |
| 5 GHz 名称 / 密码 | `jdy-cookorz5G` / `jdy-cookorz5G` |
| 无线模式 | WPA2-PSK / AES；2.4 GHz HE20，5 GHz HE80 |
| 时区 | 中国上海 |
| rc.5 转发模式 | 软件流量分载 |
| rc.5 USB 多核分流 | 默认开启 |

保留配置升级会沿用已有主机名、密码、无线及转发模式；新增加的 USB 多核分流选项默认开启，已有明确关闭设置予以保留。无线初始化可能需要约一分钟，首次登录后请修改管理与无线密码。

1. 在随身 WiFi 上开启 USB 网络共享，再连接亚瑟。
2. 打开 **网络 → 亚瑟网络面板**，查看 USB 接入、端口状态，按需运行网络质量检测。
3. 打开 **网络 → 加速与内存**，确认转发模式与 USB 多核分流状态。
4. 在 OpenClash 中导入订阅或配置后启用；其他应用通过 iStore 按需安装。

详细操作见 [使用与排查](docs/USAGE.md)。

## 加速与 OpenClash 共存

| 功能 | OpenClash 关闭、核心退出时 | OpenClash 已启用或核心仍运行时 |
| --- | --- | --- |
| 软件流量分载 / NSS | 按所选模式及兼容条件启用，两者互斥 | 暂停并清退加速规则，保留代理处理路径 |
| USB 多核分流 RPS（rc.5） | 软件模式下默认启用；运行 NSS 或全局分流接管时暂不叠加 | 默认保留，状态可在页面查看 |
| BBR | 作用于路由器本机的内核 TCP 新连接 | 可作用于代理使用的内核 TCP 连接，不替代加解密 |
| 无线 NSS | 保留独立驱动与实际状态 | 保留独立驱动与实际状态 |

RPS 负责分散收包处理，软件流量分载负责缩短符合条件连接的转发路径，两者作用不同。开启代理后的吞吐还受节点、规则、代理模式和加解密负载影响。SQM / QoS 工作时暂停转发分载以保留整形效果；USB RPS 交由独立兼容检查管理。

ZRAM 使用压缩内存；手动回收仅释放可回收缓存，不会结束代理进程或清空连接。日常内存状态应优先关注 **可用内存**。

## 源码与构建

项目定制代码和构建文件已同步到本仓库，可通过 **Code → Download ZIP** 下载，或使用：

```sh
git clone https://github.com/cookorz1/arthur-firmware.git
cd arthur-firmware
```

| 路径 | 内容 |
| --- | --- |
| [package/arthur](package/arthur) | 网络面板、USB 接入、加速与 RPS 控制、状态接口及前端代码 |
| [files](files) | 系统与无线初始化、界面定制及相关文件 |
| [scripts](scripts) | 源码整合、界面处理、版本校验与发布工具 |
| [config.seed](config.seed) / [required-packages.txt](required-packages.txt) | 固件配置与必要软件包清单 |
| [versions.env](versions.env) / [feeds.lock.json](feeds.lock.json) | 上游源码地址与固定提交 |
| [tests](tests) | 行为、界面与发布校验测试 |
| [.github/workflows](.github/workflows) | 自动构建、发布及历史固件归档流程 |

本仓库保存构建配置与定制代码，LibWrt、LuCI 等上游源码在构建时按固定提交获取。完整编译环境与命令见 [BUILDING.md](docs/BUILDING.md)；rc.5 功能源码固定在 [`01e43e4a7ffa`](https://github.com/cookorz1/arthur-firmware/tree/01e43e4a7ffaf9cd28389c317015b39444bd0047)。

## 版本记录与反馈

版本号由 `VERSION` 统一管理，[CHANGELOG.md](CHANGELOG.md) 记录每版变化。Release 固定对应源码提交，提供镜像、SHA-256 和原始构建记录；已发布版本不替换附件、不移动标签，后续修改使用新版本。

反馈问题时，请在 [Issues](https://github.com/cookorz1/arthur-firmware/issues) 提供机型、版本、刷入方式、是否保留配置、USB / WAN 接入方式及复现步骤。网络问题请附 OpenClash 模式、加速设置和必要日志，删除订阅地址、节点密码等私密信息。

SSH 查看当前设备版本与源码：

```sh
cat /etc/arthur-version
cat /etc/arthur-build
```

[版本与发布流程](docs/VERSIONING.md) · [历史固件与构建记录](.github/RELEASE_ARCHIVE.md)

## 致谢与许可

基础系统和相关组件来自 [LibWrt](https://github.com/LiBwrt/LibWrt)、[ImmortalWrt LuCI](https://github.com/immortalwrt/luci)、[Argon](https://github.com/jerrykuku/luci-theme-argon)、[iStore](https://github.com/istoreos/istore)、[OpenClash](https://github.com/vernesong/OpenClash) 和 [Mihomo](https://github.com/MetaCubeX/mihomo) 等项目。

亚瑟适配配置、网络面板和定制界面由 **cookorz** 维护。仓库自定义代码按 [MIT](LICENSE) 许可使用，各上游软件遵循各自许可证。作者头像用于本项目身份标识，不属于 MIT 代码授权范围。
