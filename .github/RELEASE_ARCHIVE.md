# 历史固件归档

[项目首页](../README.md) · [Releases 下载](https://github.com/cookorz1/arthur-firmware/releases) · [更新日志](../CHANGELOG.md)

我把此前成功编译的固件整理到 Releases，方便下载和回退。归档使用原 Actions 构建的文件，保留原文件名和 SHA-256，没有重新编译固件。

| Release | 原构建 | 主要变化 |
| --- | --- | --- |
| [build-4](https://github.com/cookorz1/arthur-firmware/releases/tag/build-4) | [#4](https://github.com/cookorz1/arthur-firmware/actions/runs/39305190653) | 初始 USB 上网、OpenClash、iStore |
| [v1.0.0](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.0.0) | [#5](https://github.com/cookorz1/arthur-firmware/actions/runs/39327147839) | 双频 Wi-Fi、Argon、端口速率、USB 开关 |
| [v1.1.0](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.1.0) | [#6](https://github.com/cookorz1/arthur-firmware/actions/runs/39379062175) | 初始化设置、无线启动和 USB 速率 |
| [v1.2.0](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.2.0) | [#7](https://github.com/cookorz1/arthur-firmware/actions/runs/39401358199) | 网络质量检测与通用随身 WiFi |
| [v1.3.0](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.3.0) | [#8](https://github.com/cookorz1/arthur-firmware/actions/runs/39446271943) | BBR、NSS 兼容保护、ZRAM、缓存回收 |
| [v1.4.0](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.4.0) | [#12](https://github.com/cookorz1/arthur-firmware/actions/runs/39477735748) | 雪山界面、定制首页、深浅色与手机布局 |
| [v1.5.0-rc.2](https://github.com/cookorz1/arthur-firmware/releases/tag/v1.5.0-rc.2) | [#14](https://github.com/cookorz1/arthur-firmware/actions/runs/39545381685) | 作者头像、署名和统一版本记录 |

较早的 `1.0.0` 到 `1.4.0` 取自当时 `luci-app-arthur` 的包版本，这次用于标识历史归档；初始构建还没有这个包，用 `build-4` 标识。所有条目按测试版 / 历史归档发布，编译成功与实机验收分别记录。

`1.5.0-rc.1` 对应的构建被取消，没有生成固件。失败或取消的构建仍保留在 Actions，不创建没有刷机文件的 Release。

## 附件怎么看

- U-Boot 刷入使用 `factory.bin`；系统内升级使用 `sysupgrade.bin`，都要匹配设备及分区布局。
- `SHA256SUMS` 保留原始固件校验值。
- `ARCHIVE_RECORD.json` 记录原构建、原产物摘要、源码提交以及两个镜像的 SHA-256。
- 包清单、构建配置及依赖记录随版本保留；最新版本还附带原构建生成的 `FIRMWARE_VERSION.json` 等版本文件。
- GitHub 自动提供的 Source code ZIP / TAR 是源码，刷机请下载 `.bin`。

## 后续维护

归档清单固定在 [release-archive.json](release-archive.json)。归档流程逐一核对成功状态、源码 SHA、原始产物摘要和固件校验值，上传到草稿后再检查附件；齐全后才公开。

如果上传中断，同一个归档工作流可以重试。已公开且校验一致的版本会直接保留，已有文件不会被覆盖。原始 Actions 产物过期后不能靠这份流程重新取回，需要保留已发布的附件。

新版本继续按 [版本发布流程](../docs/VERSIONING.md) 构建和发布，已发布的 Tag 与附件保持原样。
