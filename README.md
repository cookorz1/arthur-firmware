# Arthur · 京东云亚瑟定制固件

[![Build firmware](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml)

面向 **京东云亚瑟 AX1800 Pro / JDCloud RE-SS-01** 的 OpenWrt 定制固件，基于 **LibWrt 25.12-nss**。集成双频 Wi-Fi、Argon 中文主题、iStore 应用商店、OpenClash、F50 USB 上网，以及 WAN/LAN 端口协商速率面板，方便日常使用和维护。

**当前进度：** 基础版已成功编译，用户反馈可以使用；本次增强版新增无线初始化、Argon、端口面板、USB 开关及常用组件。增强版的构建状态以 [最新 Actions 运行](https://github.com/cookorz1/arthur-firmware/actions) 为准，新功能仍需实机验证。

## 主要功能

| 功能 | 内容 |
| --- | --- |
| 双频 Wi-Fi | 亚瑟原生 ath11k/IPQ6018 驱动、专用无线校准固件、2.4 GHz / 5 GHz AP、WPA2/WPA3 混合加密 |
| Argon 界面 | 默认 Argon 主题，中文 LuCI，集成 Argon 配置插件 |
| iStore | 原版应用商店，按需安装应用；应用依赖仍需与当前固件兼容 |
| OpenClash | 内置插件及构建时的 Mihomo ARM64 稳定核心，导入自己的配置后使用 |
| F50 USB 上网 | USB 以太网 DHCP 接入，识别 ZTE USB 网卡；保留 CDC-ECM / RNDIS / CDC-NCM 支持 |
| 端口协商速率 | “网络 → 亚瑟网络面板”分别显示 WAN、LAN1、LAN2、LAN3 的连接状态、实际协商速率和双工模式，每 3 秒刷新 |
| USB 上网开关 | 同一页面开启或关闭 F50 上网，保存并应用后生效；关闭状态在重启、重新插拔后保持 |
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

UPnP 插件默认关闭，按需启用。F50 的自动开关管理专用于 ZTE USB 以太网接入；其他 QMI/MBIM 模块和 USB 网卡可在“网络 → 接口”中手动配置。

## 首次使用

1. 电脑通过网线接入 LAN，打开 **http://192.168.10.1**。
2. 用户名为 `root`，沿用源码的无预设管理密码方式，首次登录后设置自己的管理密码。
3. 打开“网络 → 无线”，查看无线网络及初始密码，再按需要修改名称和密码。
4. 打开“网络 → 亚瑟网络面板”，查看四个网口的协商速率，并设置 USB 上网开关。
5. F50 通过 USB 连接后，默认尝试建立 `f50` DHCP 接口；如关闭 USB 上网，请在网络面板重新开启并“保存并应用”。
6. 在 iStore 中按需安装应用；OpenClash 需导入自己的订阅或配置后开启。

### Wi-Fi 默认设置

| 项目 | 默认值 |
| --- | --- |
| 2.4 GHz 名称 | `Arthur-2.4G` |
| 5 GHz 名称 | `Arthur-5G` |
| 加密 | WPA2/WPA3 混合模式 |
| 初始无线密码 | 首次启动时为每台设备独立随机生成，两频段共用；在“网络 → 无线 → 编辑”中查看 |
| 有线管理地址 | `192.168.10.1` |
| 时区 | 中国上海 |

初始密码不会写进公开仓库或构建日志。通过 SSH 也可在自己的路由器上执行 `cat /etc/arthur-wifi-password` 查看。初始化仅处理尚未设置密码的默认 AP，不覆盖已有自定义无线网络。无线信道、地区和带宽沿用无线检测默认值，可在管理页调整。

### USB 开关的范围

- **开启：** 发现 ZTE USB 网卡后建立或启用 `f50` DHCP 接口，加入 WAN 防火墙区。
- **关闭：** 关闭 `f50` 网络接口并禁止其自动启动；F50 仍然供电，USB 设备本身不会被断电。
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
5. 编译固件，检查最终包清单、自定义控制脚本、页面和 Argon 资源是否进入固件根目录。
6. 检查 factory/sysupgrade 镜像完整性、6 MiB 内核槽位限制和每个镜像的保守 60 MiB 上限，再上传产物。

构建检查及模拟测试不能代替实机无线、网口 PHY 和 USB 上网测试。主源码及独立插件的固定提交见 `versions.env`；feeds 和 Mihomo 的实际版本会随产物记录。

## 上游项目

- [LibWrt](https://github.com/LiBwrt/LibWrt) · 系统与 NSS 支持
- [ImmortalWrt LuCI](https://github.com/immortalwrt/luci) · 中文界面、Argon 主题与常用插件
- [iStore](https://github.com/istoreos/istore) · 应用商店
- [OpenClash](https://github.com/vernesong/OpenClash) · 代理管理
- [Mihomo](https://github.com/MetaCubeX/mihomo) · ARM64 代理核心

本仓库新增的配置和亚瑟网络面板采用 MIT 许可。固件中各上游组件保留各自的许可证与版权声明。
