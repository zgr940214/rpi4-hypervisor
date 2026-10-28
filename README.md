# Raspberry Pi 4 Xen lab

目标：用同一套 Yocto 工程从源码构建 Raspberry Pi 4（AArch64）的 Xen、Dom0 Linux 和唯一的 Linux guest `guest1`，一起打包成可烧录的整卡镜像。guest 由操作者手动启动。本期不包含 TEE、安全启动或加密服务。

**Yocto 自建整卡镜像已完成，并使用同一张完整镜像通过 QEMU 验证：10/10 项检查、31/31 条目标命令成功。** 静态检查 41 项通过，3 项运行或硬件检查保留为 `NOT_RUN`；辅助工具测试 99/99 通过。Pi4 实机、Pi 固件 → U-Boot 启动链仍待验证。详见[状态记录](docs/xen-lab/STATUS.md)和[本次运行报告](docs/xen-lab/evidence/yocto-image/20261028/report.json)。

## 拉取并恢复可烧录镜像

仓库包含经过验证的镜像压缩分片及清单。在已有仓库根目录执行：

```sh
git pull
python3 scripts/repo-image.py restore
```

恢复只需要 Python 3 标准库，不需要 Docker 或重新编译。脚本校验每个分片、完整压缩流和恢复后的镜像，输出 `artifacts/pi4-xen-dom0-guest1.img`：

- 大小：`1295329280` 字节。
- SHA256：`49fe88a3649b446cabcda7aa7c27ad81845bb950a3cfe602b0d057d5ab53e305`。

在 Raspberry Pi Imager 中选择 **Use Custom**，打开该 `.img`，选择目标 SD 卡并确认烧录。建议使用 8 GB 或更大的卡。镜像清单位于 [artifacts/repository-image/manifest.json](artifacts/repository-image/manifest.json)，构建版本和检查证据也随仓库提供。若要在电脑上复测同一镜像，安装 Docker Engine 后执行 `./scripts/qemu-yocto.sh validate`。

## 从源码构建并验证 Pi4 镜像

在 x86_64 Linux 或 WSL2 的 Linux 文件系统中安装 Docker Engine、Git 和 Python 3，从仓库根目录执行：

```sh
./scripts/container.sh build-container
./scripts/container.sh prepare
./scripts/container.sh parse
./scripts/container.sh plan
./scripts/container.sh build
./scripts/qemu-yocto.sh validate
```

`build-container` 创建 Ubuntu 22.04 构建环境；`prepare` 获取 `sources.lock.json` 中固定提交的构建配方、生成本地登录凭据和配置并检查 layer/provider；`parse` 和 `plan` 检查 BitBake 元数据及任务依赖；`build` 执行 `bitbake pi4-xen-dom0-image`，导出整卡镜像并检查实际产物。所有 `build.sh` 操作保留退出码及日志，位于 `local/logs/`。

这次构建由 BitBake 生成 `pi4-guest1-image` 的用户空间和 ext4 磁盘，并编译共享的 `linux-yocto` 内核。`pi4-xen-guest1` 将这份内核、guest 磁盘及包清单装入 Dom0；最终 Wic 镜像的 FAT 分区包含 Pi 启动固件、U-Boot、Xen 和内核，ext4 分区包含 Dom0 与 guest。流程获取源码、构建工具和 Pi 必需的启动固件，不采用预制的 Raspberry Pi OS 或 Debian guest 镜像。

Dom0 和 guest 根文件系统分别记录 Yocto 构建标记。guest 内核、磁盘和包清单在打包时及整卡导出后都必须与 BitBake 部署目录的原始产物匹配；检查失败会停止导出。

`qemu-yocto.sh validate` 只接受通过这些检查的 `artifacts/pi4-xen-dom0-guest1.img`，从它的 FAT 分区提取原有 Xen 与内核，直接把完整整卡镜像作为 QEMU 磁盘。Dom0 中的 guest 文件保持原样；使用 `-snapshot` 保存运行期间的临时写入，并在结束后检查源镜像哈希。缺少自建产物时命令明确失败。详情见 [QEMU 验证说明](docs/xen-lab/QEMU.md)。

部分 Yocto、GNU 原站在当前云网络中不可访问。工程已提供固定提交的 Git 镜像及校验值相同的压缩包镜像；需要改用上游同版本 Git 发布源码或另一种经过验证的源码压缩格式时，通过独立 bbappend 明确指定。原许可证检查和补丁保留，具体来源及验证证据见 [source-mirrors](docs/xen-lab/evidence/source-mirrors/20261028/)。镜像配置随仓库加载，不依赖临时修改网络设置。

`./scripts/container.sh sources` 导出实际选中配方的源码 URL、固定提交和压缩包校验值到 `local/source-manifest.json`。`scripts/mirror-sources.py` 可据此预取校验完全一致的备用压缩包；现有缓存内容不匹配时会报错，不能覆盖后继续。固定 Ubuntu 构建宿主配置位于 `meta-pi4-xen-lab/conf/build-host.inc`，目标系统的工具链和 libc 仍由 Yocto 从源码编译。

默认最多两个 BitBake 任务、每个任务两个编译线程；启用 `rm_work` 以减少磁盘占用。建议为首次 Yocto 构建准备至少 100 GiB 可用磁盘，这是工程规划值，不是本项目实测峰值。本次在初始可用约 30 GiB 的云工作盘上完成构建，期间曾触发低空间停止，清理旧实验临时文件与闲置容器层后恢复。修改 `local/site.conf` 可覆盖并行度和缓存路径。不要删除下载缓存、sstate 或全量构建目录来代替故障诊断。

无需手动安装 AArch64 交叉编译器；Yocto 会构建并选择自己的工具链。`build/conf/` 由脚本生成，有人工修改时脚本拒绝覆盖。所有依赖检出在 `.cache/sources/`，下载和 sstate 缓存分别在 `.cache/downloads/` 和 `.cache/sstate/`。

## 凭据

按用户的教学实验交付要求，下列实验专用凭据随 Git 仓库提供。准备脚本会验证配对关系并设置文件权限，重新运行不会轮换已有凭据；在新建工程中缺少整套凭据时自动生成：

- `local/credentials/id_ed25519`：电脑连接 Dom0 使用的 SSH 私钥。
- `local/credentials/id_ed25519.pub`：安装到 Dom0 root 账户的公钥。
- `local/credentials/root-password.txt`：Dom0 串口 root 登录密码。
- `local/credentials/root-password.sha512`：对应密码哈希。

运行准备脚本后这些文件权限为 `0600`；Git 不保存该权限，所以只拉取代码后直接使用 SSH 私钥时先执行 `chmod 600 local/credentials/id_ed25519`。这些已共享的凭据只用于本实验。构建仅使用公钥与哈希，日志不输出私钥或明文密码。SSH 禁用密码认证，使用公钥；guest1 的本地 Xen 控制台按教学用途自动进入 root shell。

## 产物与证据

本次构建和检查已生成：

- `artifacts/pi4-xen-dom0-guest1.img`：用于 Raspberry Pi Imager → Use Custom 的未压缩整卡镜像。
- `artifacts/SHA256SUMS`、`versions.json`：校验值、镜像大小及实际选中的版本。
- `artifacts/pi4-xen-kernel.config`、`pi4-xen-kernel.json`：最终内核配置、实际版本和源码提交。
- `artifacts/pi4-guest1.manifest`、`artifacts/checks/`：自建 guest 包清单，以及整卡中 guest 载荷与构建输出一致的检查证据。

Git 保存镜像分片、上述版本和检查文件，原始 `.img` 由 `repo-image.py restore` 恢复。自行构建时，原生 `.wic` 还保留在 `build/tmp/deploy/images/raspberrypi4-64/`。完整[构建导出日志](docs/xen-lab/evidence/yocto-image/20261028/build-export.log)、[静态检查](docs/xen-lab/evidence/yocto-image/20261028/image-checks.json)、[QEMU 串口日志](docs/xen-lab/evidence/yocto-image/20261028/serial.log)和[工具测试记录](docs/xen-lab/evidence/yocto-image/20261028/tool-tests.log)随仓库提供。

## 上板操作

烧录后，使用 3.3 V UART（GPIO14 TX、GPIO15 RX、共地，115200 8N1）捕获启动日志。启动链为 Pi 固件 → U-Boot → Xen → Dom0；接入以太网，Dom0 通过 DHCP 获取地址。在串口使用 root 和上述密码登录，通过 `ip -4 addr` 确认地址。从电脑连接：

```sh
ssh -i local/credentials/id_ed25519 root@DOM0_IP
xl info
xl list
xl dmesg
guest1-start --console
```

在 guest1 内运行 `hostname`、`uname -a`、`touch /root/write-test` 和 `guest1-counter 60`。按 Ctrl+] 回到 Dom0，然后执行：

```sh
xl list
guest1-pause-demo 3
xl console guest1
```

暂停演示只针对 `guest1`，拒绝 domain 0 和原本已暂停的 guest，并在退出时尝试恢复本次暂停的同一实例。演示时不要用其他工具并发销毁或重建 domain；Xen CLI 的检查与操作并非原子事务。

在 guest 内正常关机后，等待 `xl list` 不再列出 guest1，再执行 `guest1-start --console` 验证重复创建。默认不会自动启动 guest1。没有实际板卡日志时，上述操作均属于待实机验证步骤。

## 工具测试与镜像复查

```sh
./scripts/container.sh test
```

在构建容器内可单独检查真实产物。使用镜像构建所保留的原生工具，确保 e2fsprogs 支持构建输出启用的 ext4 特性：

```sh
source .cache/sources/poky/oe-init-build-env build
native_sysroot=$(bitbake-getvar -r pi4-xen-dom0-image --value RECIPE_SYSROOT_NATIVE)
cd ..
python3 scripts/check-image.py \
  --native-sysroot "$native_sysroot" \
  --image artifacts/pi4-xen-dom0-guest1.img \
  --deploy build/tmp/deploy/images/raspberrypi4-64 \
  --kernel-config artifacts/pi4-xen-kernel.config \
  --output artifacts/checks
```

检查器不挂载磁盘、不写入原镜像，检查结果不能代替 Pi4 实机启动、SSH、guest shell 或暂停恢复验证。

已执行的测试原始记录随仓库存放在 `docs/xen-lab/evidence/`。QEMU 命令和运行证据见 [QEMU 验证说明](docs/xen-lab/QEMU.md)。
