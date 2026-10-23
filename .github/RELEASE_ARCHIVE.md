# 固件版本与下载记录

[项目首页](../README.md) · [Releases](https://github.com/cookorz1/ax1800pro-cookwrt/releases) · [更新日志](../CHANGELOG.md)

已成功编译的固件统一发布至 Releases，便于下载与回退。镜像固定到各自的原始 Actions 构建。rc.5 已由构建流程自动发布；rc.3 与 rc.4 于 **2026-10-22** 补充归档，原始镜像与旧版附件保持不变。

## 已发布版本

| 版本 | 主要变化 | 原构建 |
| --- | --- | --- |
| [**v1.5.0-rc.5**](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.5.0-rc.5) | 默认 USB RPS、OpenClash 运行时保留多核分流、Wi-Fi 转发实测反馈 | [#17](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39768121777) |
| [v1.5.0-rc.4](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.5.0-rc.4) | USB 软件分载、NSS 互斥与 OpenClash 兼容保护 | [#16](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39605685842) |
| [v1.5.0-rc.3](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.5.0-rc.3) | 标签页标题、作者头像图标与缓存引用修复 | [#15](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39564528452) |
| [v1.5.0-rc.2](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.5.0-rc.2) | 作者头像、署名和统一版本记录 | [#14](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39545381685) |
| [v1.4.0](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.4.0) | 雪山界面、定制首页、深浅色与手机布局 | [#12](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39477735748) |
| [v1.3.0](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.3.0) | BBR、NSS 兼容保护、ZRAM、缓存回收 | [#8](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39446271943) |
| [v1.2.0](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.2.0) | 网络质量检测与通用随身 WiFi | [#7](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39401358199) |
| [v1.1.0](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.1.0) | 初始化设置、无线启动和 USB 速率 | [#6](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39379062175) |
| [v1.0.0](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/v1.0.0) | 双频 Wi-Fi、Argon、端口速率、USB 开关 | [#5](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39327147839) |
| [build-4](https://github.com/cookorz1/ax1800pro-cookwrt/releases/tag/build-4) | 初始 USB 上网、OpenClash、iStore | [#4](https://github.com/cookorz1/ax1800pro-cookwrt/actions/runs/39305190653) |

所有条目均按测试候选版或历史归档标记为 Pre-release。最新测试候选版是 **rc.5**，已收到 [USB 共享经 Wi-Fi 的实测反馈](../docs/PERFORMANCE.md)；早期的 `1.0.0～1.4.0` 名称取自当时的界面包版本，不代表后来补做了稳定版实机验收。初始构建没有独立项目版本号，以 `build-4` 标识。

`1.5.0-rc.1` 的构建被取消，没有生成可发布镜像。失败或取消的记录仍在 Actions，不创建空的 Release。

## 下载与校验

- U-Boot 刷入使用 `factory.bin`；系统内升级使用 `sysupgrade.bin`，都要匹配设备及分区布局。
- `SHA256SUMS` 是原始镜像的校验值。
- 历史补发版本的 `ARCHIVE_RECORD.json` 固定记录原构建、原产物摘要、源码提交及两份镜像的 SHA-256；正常自动发布的 rc.5 使用 `FIRMWARE_VERSION.json` 记录来源。
- 近期版本附带 `FIRMWARE_VERSION.json`、原始更新说明、包清单与依赖版本；旧版的默认设置以对应提交为准。
- GitHub 自动提供的 Source code ZIP / TAR 是源码，刷机请下载附件中的 `.bin`。

## 归档规则

[release-archive.json](release-archive.json) 固定版本、成功构建 ID、产物 ID、源码提交和 ZIP 摘要。归档时先验证来源及镜像校验值，再上传草稿；附件齐全且校验一致后才公开。

上传中断时可以重试原归档流程。已公开且内容一致的版本会保留，已有 Tag 与附件不覆盖。Actions 产物有保留期限，过期后不能靠原下载地址找回，因此固定版本使用 Releases 保存。

后续版本遵循 [版本记录与发布流程](../docs/VERSIONING.md)。源码版本、构建成功、发布状态和实机反馈分别记录。

## 仓库改名后的兼容

当前仓库地址为 `cookorz1/ax1800pro-cookwrt`，下载链接、API 请求和后续构建记录使用新地址。历史归档计划中的 `record_repository` 则保留各版原始命名空间，用于重现已发布的 `ARCHIVE_RECORD.json` 与说明，避免旧附件摘要因改名而变化。无需覆盖或重新上传旧版固件。
