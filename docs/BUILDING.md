# 构建说明

[返回项目首页](../README.md) · [版本发布流程](VERSIONING.md)

## 构建与验证

在 GitHub Actions 中手动选择 **Run workflow**，或提交构建相关文件到 `main` 分支。流程依次执行：

1. 测试端口状态读取、USB 关闭/重启/插拔后的状态、重新启用，以及无线初始化和页面渲染。
2. 取得固定提交的 LibWrt、OpenClash、iStore，安装 feeds，生成配置。
3. 按 `required-packages.txt` 核对无线、主题、商店、驱动和网络面板是否确实被选中。
4. 下载 Mihomo ARM64 稳定核心，核对发布摘要（如提供）及 ELF 架构，并记录版本和 SHA-256。
5. 编译固件，检查最终包清单、IPQ6018 运行固件及板级数据、自定义控制脚本、密码哈希、页面和 Argon 资源是否进入固件根目录。
6. 检查 factory/sysupgrade 镜像完整性、6 MiB 内核槽位限制和每个镜像的保守 60 MiB 上限，再上传产物。

构建检查及模拟测试不能代替实机无线、网口 PHY、USB 上网和代理规则命中测试。发布前检查 OpenClash 生命周期钩子、BBR/FQ/ZRAM 模块和版本化页面资源；feeds 固定提交及 Mihomo 的实际版本随产物记录。

