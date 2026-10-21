# 版本记录与发布

维护者与定制作者：**by-cookorz**。LibWrt、LuCI、Argon 及插件保留各自的版权和来源。

## 三种记录各司其职

| 记录 | 作用 | 保存方式 |
| --- | --- | --- |
| `VERSION` | 当前源码准备构建的项目版本 | 例如 `1.5.0-rc.1`，不带前缀 v |
| `CHANGELOG.md` | 面向用户的变更记录 | 每版写新增、调整、修复、验证状态；历史构建补记与正式发布分开 |
| GitHub Release + Tag | 固定一次可下载的版本 | 例如 `v1.5.0-rc.1`，成功后不覆盖附件或移动标签 |
| Actions 构建编号 | 追踪同一版本的开发构建 | 如 `#13`，不把编号当项目版本号；Artifacts 会过期 |

版本升级约定：不兼容的配置/升级方式变更升主版本，新增功能升功能版本，修复升修订版本。新功能或界面先用 `-rc.1`、`-rc.2`；确认实机表现后再记录不带 rc 的版本。一次候选版尚未发布时可以继续修订源码，提交 SHA 区分各次构建；发布后必须换版本。

## 每次更新怎么做

1. 修改 `VERSION`，并同步 `package/arthur/Makefile` 的基础版本。例如项目 `1.5.0-rc.1` 对应包版本 `1.5.0`；包的修订单独用 `PKG_RELEASE`。
2. 在 `CHANGELOG.md` 顶部新增同名、带日期的条目。写清用户能看到的变化、修复内容、已做的检查和仍待实机验证的事项。不要把“编译成功”写成“已经实测稳定”。
3. 提交到 main，等待 Actions 的功能测试、界面检查和编译校验。普通 push 只产生测试构建与 Artifacts。
4. 实机验证时记录机型、刷入方式、是否保留配置、WAN/USB/Wi-Fi、OpenClash模式及加速开关组合、结果和发现的问题。敏感订阅、节点密码不写进记录。

## 在 GitHub 发布一个固定版本

1. 打开 **Actions → Build jdy-cookorz Arthur firmware → Run workflow**，分支选 **main**。
2. 勾选“构建成功后发布 VERSION 对应的 GitHub Release”，再运行。
3. 流程重新验证和构建这一提交；成功后生成 Release 草稿、上传附件并校验附件是否齐全，再公开发布。`-rc.N` 自动标为 Pre-release，不替换 Latest 正式版；不带 rc 的版本才标为正式发布。
4. 若中途上传或校验失败，保留草稿用于检查。不要手工把不完整草稿发布。已有 Release 或 Tag 会阻止覆盖，需检查现有记录并采用新版本。

发布使用该次构建的 GitHub token，无需在仓库里保存个人 token；只有发布 job 申请 `contents: write`，普通构建保持只读。

## 用户如何确认自己刷了什么

- 登录页和管理侧栏显示项目版本及 `by-cookorz`。
- SSH：`cat /etc/arthur-version` 查看版本，`cat /etc/arthur-build` 查看完整构建提交；`cat /etc/arthur-release.json` 查看来源记录。
- 下载名示例：`jdy-cookorz-arthur-v1.5.0-rc.1-abcdef123456-factory.bin`。同包提供 `sysupgrade.bin`，请按刷入方式选择。
- 将 `FIRMWARE_VERSION.json` 与 `SHA256SUMS` 一起保留。前者记录镜像名称、用途、大小、哈希、源码提交、构建链接、源码/feeds 锁定版本；SHA-256 用来确认文件完整性，不代替实机验证。

U-Boot 刷入使用 factory 镜像；系统内升级使用 sysupgrade 镜像。完整镜像仍经过原有机型、内核分区大小及固件体积检查，命名变化不改变文件格式。

## 实机验收记录模板

| 项目 | 记录 |
| --- | --- |
| 项目版本 / 完整 SHA | |
| 机型 / 刷入方式 / 保留配置 | |
| WAN / USB 上网 | |
| 2.4 GHz / 5 GHz | |
| OpenClash 模式 / NSS / QoS 设置 | |
| 网络检测、协商速率、内存回收 | |
| 发现的问题、重现步骤、是否回滚 | |

如需回滚，下载旧 Release 的对应镜像和校验文件；保持旧版本记录完整，不用新镜像替换旧附件。
