<div align="center">

<img src="package/arthur/files/www/luci-static/arthur/avatar.jpg" width="96" height="96" alt="cookorz 的头像">

# jdy-cookorz

京东云亚瑟 AX1800 Pro 定制固件 · **by-cookorz**

[![构建状态](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml/badge.svg)](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml)

[下载版本](https://github.com/cookorz1/arthur-firmware/releases) · [历史版本](.github/RELEASE_ARCHIVE.md) · [测试构建](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml) · [更新日志](CHANGELOG.md) · [使用说明](docs/USAGE.md)

</div>

## 我想把亚瑟做成什么样

我是 cookorz，这里放的是我为京东云亚瑟整理的定制固件，系统基于 LibWrt。我最初想解决的事情很简单：插上随身 WiFi 就能共享网络，常用应用方便安装，打开管理页面就能看清网络和设备状态。

现在我把双频 Wi-Fi、iStore、OpenClash、USB 上网、端口速率和网络检测放进了同一套界面，也加上了 BBR、NSS 兼容管理和内存面板。界面以 Argon 为基础，保留雪山登录页、中文菜单和深浅色切换，Logo 与标签页图标统一用我的头像。

后面我会继续围绕这台设备完善功能。涉及驱动、无线和加速的调整，我会在更新日志里写清楚改动及验证范围；实机表现也欢迎带上版本号反馈。

## 适用设备与版本

| 项目 | 说明 |
| --- | --- |
| 设备 | **京东云亚瑟 AX1800 Pro / JDCloud RE-SS-01** |
| 板型 | `jdcloud,re-ss-01` |
| 编译目标 | `qualcommax/ipq60xx`，IPQ6018 |
| 当前源码版本 | [VERSION](VERSION)；改动记录在 [CHANGELOG.md](CHANGELOG.md) |
| 发布版本 | [Releases](https://github.com/cookorz1/arthur-firmware/releases)，`rc` 标记为测试候选版 |
| 构建记录 | [Actions](https://github.com/cookorz1/arthur-firmware/actions/workflows/build.yml)，可查看对应提交与检查结果 |

这份配置针对 RE-SS-01，请先确认板型和分区布局。编译检查、浏览器检查和实机验证分别记录，具体版本的状态以对应构建及发布说明为准。

## 下载和刷入

我把固定版本放在 Releases。如果这里还没有下载包，先到 Actions 找成功构建。还没发布的改动，可以到 Actions 选择对应提交的**成功构建**，在页面底部 Artifacts 下载固件包。下载 Artifacts 通常需要登录 GitHub，文件也有保留期限。

新的固件包按 `jdy-cookorz-v版本号-提交前12位-构建编号` 命名。下载 ZIP 后先解压，再选择里面的 `.bin`：

| 文件 | 用途 |
| --- | --- |
| `jdy-cookorz-arthur-v版本号-提交前12位-factory.bin` | 兼容本镜像格式的 **U-Boot 刷机** |
| `jdy-cookorz-arthur-v版本号-提交前12位-sysupgrade.bin` | 匹配本机板型及分区布局的系统内升级 |
| `SHA256SUMS` | 校验固件文件完整性 |
| `FIRMWARE_VERSION.json` | 版本、源码提交、构建链接、依赖版本及镜像校验值 |
| `RELEASE_NOTES.md` | 这一版的更新说明与刷入提示 |

较早的构建可能使用上游文件名，按 `factory.bin` / `sysupgrade.bin` 后缀区分。你用 U-Boot 刷入时选择 **factory.bin**，同时核对自己的 U-Boot 和分区布局。ZIP 需要解压，改后缀不能把压缩包变成固件。刷机前备份自己的配置；本项目不负责更改 U-Boot 或重新分区。

Windows 可用 PowerShell 核对校验值，并与 `SHA256SUMS` 对照：

```powershell
Get-FileHash .\实际固件文件名.bin -Algorithm SHA256
```

Linux / macOS 可在解压目录执行 `shasum -a 256 -c SHA256SUMS`。

## 第一次开机

建议先用网线接 LAN，打开 **http://192.168.10.1**。

| 项目 | 初始值 |
| --- | --- |
| 主机名 | `jdy-cookorz` |
| 管理账号 / 密码 | `root` / `password` |
| 2.4 GHz 名称 / 密码 | `jdy-cookorz2.4G` / `jdy-cookorz2.4G` |
| 5 GHz 名称 / 密码 | `jdy-cookorz5G` / `jdy-cookorz5G` |
| 无线模式 | WPA2-PSK / AES；2.4 GHz HE20，5 GHz HE80 |
| 时区 | 中国上海 |

这些是全新安装或恢复出厂设置时的初始值。保留配置升级会沿用原设置。无线初始化可能需要约一分钟，首次登录后请修改管理密码和 Wi-Fi 密码。

随身 WiFi 先开启 USB 网络共享，再接入路由器。到 **网络 → 亚瑟网络面板** 查看连接、控制 USB 上网开关，或手动检测网络质量。OpenClash 需要导入自己的配置后启用；应用可在 iStore 按需安装。

## 已经集成的功能

| 功能 | 在哪里、能做什么 |
| --- | --- |
| 定制首页 | WAN / USB 实时流量、CPU、可用内存、存储、端口状态和常用应用入口 |
| 中文管理界面 | Argon 定制样式、雪山登录页、头像标志、`by-cookorz` 署名、版本显示、手机布局与深浅色切换 |
| 双频 Wi-Fi | 亚瑟原生 ath11k 驱动及板级固件，2.4 GHz / 5 GHz AP |
| iStore / OpenClash | 应用商店、OpenClash 和构建时记录版本的 Mihomo ARM64 核心 |
| USB 网络共享 | CDC-ECM / RNDIS / CDC-NCM 随身 WiFi 的 DHCP 接入；开关状态重启、重新插拔后保留 |
| 端口协商速率 | WAN、LAN1–LAN3、USB 网卡实际链路速率，另列 USB 总线枚举速率 |
| 网络质量检测 | 手动检测 WAN / USB 的 IPv4、延迟、丢包和 HTTPS 可达性 |
| 性能与内存 | BBR / Cubic、NSS 自动兼容保护、128 MiB ZRAM、可用内存与手动缓存回收 |
| 常用驱动与工具 | USB 网卡与存储驱动、QMI / MBIM、常见文件系统、DDNS、WOL、流量统计、TTYD、SFTP、iperf3、ethtool 等 |

完整操作、USB 设备识别范围、无线排查以及性能设置说明放在 [使用与排查](docs/USAGE.md)。

有几处容易误会，我单独说明一下：

- 端口速率和 USB 总线速率代表链路状态；网络测速、宽带带宽和蜂窝信号强度需要分别判断。当前网络检测不读取 RSRP / SINR 或光猫光功率。
- USB 开关控制网络接入，关闭后随身 WiFi 仍会供电。为了兼容旧配置，内部接口名继续使用 `f50`，页面统一显示“随身 WiFi”。
- OpenClash 启用或运行时，兼容保护会暂停 NSS 的 ECM 转发加速；SQM / QoS 等冲突条件也会触发保护。BBR 作用于路由器本机的 TCP 连接，实际提升取决于使用场景。
- 内存面板以 **MemAvailable** 为主要参考。手动回收只清理可回收缓存，设有 60 秒冷却；系统没有配置定时清缓存。ZRAM 是压缩交换空间。

## 我怎么维护版本

源码版本统一写在 `VERSION`，登录页、侧栏和固件文件名都从它生成。每次更新先在 [更新日志](CHANGELOG.md) 写清内容，再由 Actions 检查、构建，并保存源码提交、依赖清单和 SHA-256。

开发构建用 Actions 编号区分；需要固定下载地址时，再按 [版本记录与发布流程](docs/VERSIONING.md) 发布 Release。测试候选版使用 `-rc.N`，已发布的版本和 Tag 保留原样，需要修正就发新版本，方便找回旧包和核对问题。

如果你也想自行编译，见 [构建说明](docs/BUILDING.md)。

## 反馈问题

可以到 [Issues](https://github.com/cookorz1/arthur-firmware/issues) 留下设备板型、固件版本、刷入方式、是否保留配置，以及复现步骤。网络问题请附上 WAN / USB 类型、OpenClash 与 NSS / QoS 的状态；日志里记得去掉订阅地址、节点密码和其他私密信息。

SSH 中可以用这两条命令确认当前固件：

```sh
cat /etc/arthur-version
cat /etc/arthur-build
```

## 致谢与许可

这份固件建立在 [LibWrt](https://github.com/LiBwrt/LibWrt)、[ImmortalWrt LuCI](https://github.com/immortalwrt/luci)、[Argon](https://github.com/jerrykuku/luci-theme-argon)、[iStore](https://github.com/istoreos/istore)、[OpenClash](https://github.com/vernesong/OpenClash) 和 [Mihomo](https://github.com/MetaCubeX/mihomo) 等项目之上，感谢这些项目的维护者。

我主要维护这里的亚瑟适配配置、网络面板和定制界面。仓库的自定义代码按 [MIT](LICENSE) 许可使用，各上游软件继续遵循各自许可证。头像仅用作本项目的作者标识，不属于 MIT 代码授权范围。
