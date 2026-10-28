# Raspberry Pi 4 Xen lab

目标：Raspberry Pi 4（AArch64）启动 Xen、Dom0 Linux，并由操作者手动启动唯一的 Linux guest `guest1`。本期不包含 TEE、安全启动或加密服务。

**当前状态：基础工程已建立，工具测试通过；官方 Yocto 源站的网络访问阻塞了完整构建，目前没有可烧录镜像，也没有 Xen 系统启动通过的结论。** 以 [状态和验证记录](docs/xen-lab/STATUS.md) 为准。

## 构建

在 Linux 或 WSL2 的 Linux 文件系统中工作，安装 Docker Engine 后，从仓库根目录执行：

```sh
./scripts/container.sh build-container
./scripts/container.sh prepare
./scripts/container.sh parse
./scripts/container.sh build
```

`build-container` 创建 Ubuntu 22.04 构建环境；`prepare` 获取 `sources.lock.json` 中固定提交的依赖、生成本地登录凭据和配置并检查 layer/provider；`parse` 检查 BitBake 元数据；`build` 构建、导出整卡镜像并执行只读检查。所有 build.sh 操作保留退出码及日志，位于 `local/logs/`。尚未验证的命令不能视为已构建成功。

默认最多两个 BitBake 任务、每个任务两个编译线程；启用 `rm_work` 以减少磁盘占用。建议为首次 Yocto 构建准备至少 100 GiB 可用磁盘，这是工程规划值，不是本项目实测峰值。现有云工作盘只有约 30 GiB，磁盘监视器会在空间不足时停止任务，不能保证全量构建能容纳。修改 `local/site.conf` 可覆盖并行度和缓存路径。不要删除下载缓存、sstate 或全量构建目录来代替故障诊断。

无需手动安装 AArch64 交叉编译器；Yocto 会构建并选择自己的工具链。`build/conf/` 由脚本生成，有人工修改时脚本拒绝覆盖。所有依赖检出在 `.cache/sources/`，下载和 sstate 缓存分别在 `.cache/downloads/` 和 `.cache/sstate/`。

## 凭据

按用户的教学实验交付要求，下列实验专用凭据随 Git 仓库提供。准备脚本会验证配对关系并设置文件权限，重新运行不会轮换已有凭据；在新建工程中缺少整套凭据时自动生成：

- `local/credentials/id_ed25519`：电脑连接 Dom0 使用的 SSH 私钥。
- `local/credentials/id_ed25519.pub`：安装到 Dom0 root 账户的公钥。
- `local/credentials/root-password.txt`：Dom0 串口 root 登录密码。
- `local/credentials/root-password.sha512`：对应密码哈希。

运行准备脚本后这些文件权限为 `0600`；Git 不保存该权限，所以只拉取代码后直接使用 SSH 私钥时先执行 `chmod 600 local/credentials/id_ed25519`。这些已共享的凭据只用于本实验。构建仅使用公钥与哈希，日志不输出私钥或明文密码。SSH 禁用密码认证，使用公钥；guest1 的本地 Xen 控制台按教学用途自动进入 root shell。

## 构建成功后的产物

成功构建和检查后，导出脚本生成：

- `artifacts/pi4-xen-dom0-guest1.img`：用于 Raspberry Pi Imager → Use Custom 的未压缩整卡镜像。
- `artifacts/SHA256SUMS`、`versions.json`：校验值、镜像大小及实际选中的版本。
- `artifacts/pi4-xen-kernel.config`、`artifacts/checks/`：最终内核配置及静态检查证据。

这些是预期输出路径，文件不存在时不能烧录。原生 `.wic` 保留在 `build/tmp/deploy/images/raspberrypi4-64/`。建议使用 8 GB 或更大的卡，并以最终镜像实际字节数确认卡容量。使用 Imager 烧录需要用户选择并确认实体存储设备。

## 上板操作

构建通过后，使用 3.3 V UART（GPIO14 TX、GPIO15 RX、共地，115200 8N1）捕获启动日志。启动链为 Pi 固件 → U-Boot → Xen → Dom0；接入以太网，Dom0 通过 DHCP 获取地址。在串口使用 root 和上述密码登录，通过 `ip -4 addr` 确认地址。从电脑连接：

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

在构建容器内可单独检查真实产物：

```sh
python3 scripts/check-image.py \
  --image artifacts/pi4-xen-dom0-guest1.img \
  --deploy build/tmp/deploy/images/raspberrypi4-64 \
  --kernel-config artifacts/pi4-xen-kernel.config \
  --output artifacts/checks
```

检查器不挂载磁盘、不写入原镜像，检查结果不能代替 Pi4 实机启动、SSH、guest shell 或暂停恢复验证。

已执行的测试原始记录随仓库存放在 `docs/xen-lab/evidence/`。QEMU 可覆盖的范围及尚未执行的步骤见 [QEMU 验证说明](docs/xen-lab/QEMU.md)。
