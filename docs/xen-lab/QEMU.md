# 自建 Pi4 镜像的 QEMU 验证

本项目的验收入口是 `scripts/qemu-yocto.sh`：使用 Yocto 构建的同一张 Pi4 整卡镜像运行 Xen、Dom0 和其内嵌 guest1。**当前 Pi4 源码构建受网络 403 阻塞，尚无该整卡产物；此入口的运行验证状态为 NOT_RUN。** 已完成的 Debian QEMU 实验见文末历史记录。

## 构建和运行

需要 x86_64 Linux，或 WSL2 的 Linux 文件系统，以及可用的 Docker Engine、Git 和 Python 3。在仓库根目录执行：

```sh
./scripts/container.sh build-container
./scripts/container.sh prepare
./scripts/container.sh parse
./scripts/container.sh plan
./scripts/container.sh build
./scripts/qemu-yocto.sh validate
```

`build` 通过 BitBake 从源码编译 Xen、工具栈、Pi4 内核以及 Dom0/guest 用户空间，将自建 `pi4-guest1.ext4` 装入 Dom0，再生成 Wic 整卡镜像。导出位置为 `artifacts/pi4-xen-dom0-guest1.img`。该路径不存在时，QEMU 入口退出失败；它不自动创建其他发行版的验证磁盘。

`qemu-yocto.sh prepare` 可以单独检查构建证据并提取启动载荷。默认的 `validate` 会执行相同准备检查后启动仿真。构建或目标脚本变化后，需要先重新运行 `container.sh build`，再验证新产物。

## 使用同一份构建产物

准备脚本核对以下证据：

- `versions.json` 的构建系统、Pi4 机器型号、源码锁文件，以及实际选中的 Dom0、guest、内核和 Xen 配方。
- 整卡静态检查成功，镜像和最终内核配置哈希与检查记录一致。
- Dom0/guest 的 Yocto 构建标记、内嵌 guest 磁盘与内核、包清单均与 BitBake 部署产物匹配。
- 同一个 Pi4 内核内建 Xen、GICv3、virtio MMIO/块设备/网卡与 MBR 分区驱动，支持这套 QEMU 启动方式。

脚本仅从整卡 FAT 分区提取已有 `xen` 和 `Image`；原始完整 `.img` 作为 virtio 磁盘传入 QEMU，Dom0 使用第二分区 `/dev/vda2`。guest 继续使用 Dom0 中原有的 `/var/lib/xen/images/guest1/`，不替换其 rootfs、内核或配置，也不添加外部 initramfs。Wic 使用 UUID 生成分区挂载信息。

仿真器采用 `virt,gic-version=3,virtualization=on`、Cortex-A57、2 CPU、1536 MiB RAM 和 TCG。Dom0 为 512 MiB，guest1 为 256 MiB、1 vCPU；无需宿主 ARM KVM。Docker 镜像只提供宿主仿真与检查工具，来宾软件取自上述 Yocto 产物。

Dom0 串口使用仓库实验密码登录，SSH 使用仓库公钥；guest hvc0 自动进入 root shell。密码输入不写入控制器发送日志。

## 自动检查与证据

验证控制器会执行以下流程，并把未到达的步骤保留为 `NOT_RUN`：

1. 观察 Xen 启动，进入 Dom0，执行 `xl info`、`xl list`、`xl dmesg`，确认初始只有 Domain-0。
2. 手动运行 `guest1-start --console`，检查 guest 的 ARM64 shell、主机名和磁盘写入。
3. 通过 SSH 公钥认证到 Dom0，再连接已有 guest 控制台。
4. 暂停 guest，检查状态和计数停止，确认 Dom0 仍可执行命令；恢复后检查计数继续、UUID 不变和 shell 可用。
5. 正常关闭 guest，等待域清理完成；重新创建 guest，读取之前写入的文件，再次正常关机。
6. 结束 QEMU 并检查原始整卡 SHA256，确认 `-snapshot` 临时覆盖层没有改变输入镜像。

准备记录位于 `local/qemu-yocto/provenance.json`，运行证据位于 `local/qemu-yocto/results/<UTC时间>/`，包括 `report.json`、`serial.log` 和 `ssh-guest-console.log`；命令总日志在 `local/qemu-yocto/logs/validation.log`。报告记录实际启动命令、载荷哈希、目标命令输出与退出码。只有整轮完成且各项检查通过，才能报告自建镜像 QEMU PASS。

本机型是通用 ARM `virt`。运行成功可验证自建 Xen、Dom0、guest 及其管理脚本；Pi 固件 → U-Boot 的启动链、Pi4 设备树、SD 卡与 GENET 网卡仍需上板验证。QEMU 直接加载从 Pi4 整卡取出的 Xen，未执行 U-Boot。

## 历史 Debian QEMU 实验

2026-10-28 16:45–16:47（北京时间），独立的 Debian bookworm ARM64 根文件系统与 Linux 6.1.190（`6.1.0-54-arm64`）搭配自行编译的 Xen 4.19.0，在 QEMU 6.2.0 `virt` 上完成了 10/10 项检查、31/31 条目标命令，脚本退出码为 0。此实验验证了 Xen 管理流程，**没有使用 Yocto 自建 Pi4 镜像，不能作为当前交付要求的通过结果**。

保留的历史证据：

- [逐项报告](evidence/qemu/20261028/report.json)。
- [原始串口日志](evidence/qemu/20261028/serial.log)。
- [SSH 与 guest 控制台日志](evidence/qemu/20261028/ssh-guest-console.log)。
- [当时的 49 项辅助工具测试](evidence/qemu/20261028/helper-tests.log)。

旧入口 `scripts/qemu.sh prepare/validate` 和 `local/qemu/` 只用于复现该独立实验，正式自建镜像验证使用前述 `scripts/qemu-yocto.sh`。
