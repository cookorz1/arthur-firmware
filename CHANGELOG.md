# 更新日志

项目维护与界面定制：**by-cookorz**。版本号遵循 `主版本.功能版本.修订版本`，测试候选版使用 `-rc.N`。

## [1.5.0-rc.1] - 2026-10-21

### 界面与品牌
- 新增 C 字母与连接节点组成的矢量 Logo，统一登录页、侧栏和浏览器图标；保留三套标志提案供作者选择。
- 登录页与管理侧栏增加 `by-cookorz` 署名，同时保留 LuCI / LibWrt / Argon 上游来源信息。
- 在登录页和侧栏显示固件版本，保留每次构建独立的资源缓存标识。

### 版本管理
- 新增统一 `VERSION`、中文更新日志和版本发布说明。
- 构建输出包含版本、提交、构建编号、上游锁定版本、镜像文件大小及 SHA-256 的版本清单。
- 固件按项目版本与源码提交命名，区分 U-Boot 用 factory 与系统内升级用 sysupgrade。
- 增加手动发布入口：构建和校验通过后上传附件，先生成草稿，附件确认完整后发布 Release；已有标签或版本不覆盖。

### 验证状态
- 此条目记录源码变更；构建是否完成以对应 Actions 为准。
- `rc` 表示候选版本，实机启动、无线、USB 及 OpenClash 共存仍需验收；不据此宣称吞吐提升。

## [1.4.0] - 2026-10-21

历史构建基线补记，对应源码 [`2f38f92`](https://github.com/cookorz1/arthur-firmware/commit/2f38f92cf70b9865d3a54b567404464ca5be92f7)，并非已有同名发布标签。

- 加入 jdy-cookorz 雪山风格首页、统一登录页、深色侧栏及深浅切换。
- 首页展示 WAN / USB 实时流量、CPU、内存、系统存储、端口速率、邻居设备与加速保护状态。
- 增加管理功能搜索，以及 OpenClash、iStore、网络检测、加速与内存快捷入口。
- 修复深色数字对比度和手机菜单按钮；检查五种屏幕宽度。
- [Actions #12](https://github.com/cookorz1/arthur-firmware/actions/runs/39477735748) 构建成功；通过 49 个 Python 用例、三组 Node 检查与浏览器布局检查。实机验收单独记录。

## [1.3.0] - 2026-10-20

历史构建基线补记，对应源码 [`23dcca5`](https://github.com/cookorz1/arthur-firmware/commit/23dcca586abf380f4bbf5619a51e50fd43cf155b)，并非已有同名发布标签。

- 加入 BBR / Cubic、NSS 路由加速兼容保护、ZRAM 和手动缓存回收。
- OpenClash 启停及重载时保护代理转发；根据 QoS / 多核转发状态暂停 NSS。
- 保留 USB 热插拔、开关、网络检测和各端口速率功能。
- [Actions #8](https://github.com/cookorz1/arthur-firmware/actions/runs/39446271943) 构建成功，性能与共存效果仍以实机结果为准。

## 更早的构建

早期 Actions 编号用于追踪 USB 上网、Wi-Fi、中文界面、Argon、iStore、端口速率与网络检测等开发过程，不回填未经发布的正式 Tag。

[1.5.0-rc.1]: https://github.com/cookorz1/arthur-firmware/blob/main/VERSION
