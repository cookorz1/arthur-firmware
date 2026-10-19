# 京东云亚瑟 AX1800 Pro 定制编译

状态：已于 2026-10-20 启动首次 GitHub Actions 云编译，尚未生成或实机验证固件。

查看编译进度：https://github.com/cookorz1/arthur-firmware/actions/runs/39303738645

## 已配置的功能

- LibWrt 25.12-nss，qualcommax/ipq60xx，专用设备 `jdcloud_re-ss-01`。请核实底部型号为 RE-SS-01。
- 中文 LuCI 管理界面，iStore 原版应用商店，OpenClash，编译时下载并内置 Mihomo 稳定版 ARM64 核心。
- USB 3.0、CDC-ECM、RNDIS、CDC-NCM 驱动和 usb-modeswitch；ZTE USB 网卡插入时建立 DHCP 接口 `f50` 并加入 WAN 防火墙区。
- 终端、USB 存储、ext4 和挂载工具，便于后续维护。

F50 以 USB 以太网模式使用，F50 自己负责 SIM 卡拨号。此项目不把它改为串口拨号。自动识别按 ZTE USB 厂商 ID `19d2`，尚待实机验证；其他 ZTE USB 网卡也会匹配。可在网络 → 接口中手动检查 `f50` 对应设备。

## 云编译

1. 建立独立 GitHub 仓库，默认分支使用 `main`，初始化 README。
2. 把本目录内的文件放在仓库根目录，保留 `.github/workflows/build.yml`。不要把 `arthur-firmware` 整层当作仓库子目录上传。浏览器的拖放可能漏掉隐藏目录；工作流可用 GitHub 的 Add file → Create new file 创建，文件名填写 `.github/workflows/build.yml` 并粘贴本项目同名文件内容。
3. 提交会触发编译，也可打开 Actions → Build Arthur F50 OpenClash iStore → Run workflow。
4. 等全部步骤成功后，在该次运行的 Artifacts 下载 `Arthur-F50-OpenClash-iStore-*`。
5. 如果失败，下载日志继续排查；失败运行不提供“编译成功”的固件产物。

固定了主源码、OpenClash、iStore 的提交；软件 feeds 和 Mihomo 稳定版在编译时解析，并把实际版本、配置、包清单、校验值一起保存。上游变动或依赖问题仍可能导致首次编译需要调整。

## 默认设置

- 管理地址：http://192.168.10.1 （避开 F50 常见的管理网段）
- 用户名：root；沿用源码的无预设密码方式，首次进入后自行设置密码。
- 时区：中国上海；无线设置沿用设备源码默认值，进入管理页后设置 Wi-Fi。
- OpenClash 需导入自己的订阅或配置后开启；项目不包含订阅或节点凭据。
- iStore 已选中；商店内个别应用可能受架构、包管理器、固件版本或内核模块依赖限制。集成应用商店不等于完整 iStoreOS，也不保证每个应用可安装。
- 保留源码的 NSS 相关默认配置。代理流量能否使用加速取决于 OpenClash 的工作模式，不保证所有流量走 NSS。

## 固件与分区

不修改分区表、不写 U-Boot、不刷设备。构建使用源码设备默认镜像格式，并检查：设备选择和必要包保留、内核不超过上游 6144 KiB 槽位、factory 和 sysupgrade 镜像均存在、包清单完整、每个镜像不超过保守的 60 MiB 上限。

这些检查不能确认你当前路由器的实际分区。刷机前仍需查看当前系统和磁盘布局；不能仅凭文件名中的 factory/sysupgrade 决定能否刷入，不能强制跳过机型校验。

在路由器 SSH 中可执行下列只读命令，把输出提供给协助者确认：

```sh
ubus call system board
cat /proc/partitions
cat /proc/mtd
ls -l /dev/disk/by-partlabel 2>/dev/null
lsblk -o NAME,SIZE,TYPE,FSTYPE,PARTLABEL,MOUNTPOINTS 2>/dev/null
```

## 来源

- https://github.com/LiBwrt/LibWrt
- https://github.com/vernesong/OpenClash
- https://github.com/istoreos/istore
- https://github.com/MetaCubeX/mihomo
