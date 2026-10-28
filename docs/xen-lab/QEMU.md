# QEMU 运行验证

**QEMU 实测通过：10/10 项检查通过，31/31 条目标命令退出码为 0，验证脚本退出码为 0。** Xen 4.19.0、Dom0 和 guest1 已实际运行，SSH、可写根文件系统、暂停恢复、正常关机与重新创建均通过。[查看原始报告](evidence/qemu/20261028/report.json)。

运行时间：2026-10-28 16:45–16:47（北京时间）；原始运行目录 `20261028T084517Z`，报告时间戳使用 UTC。本次平台为通用 ARM `virt` 和独立的 Debian 验证镜像，Pi4 整卡构建与上板验证仍未完成。

## 从仓库复现

需要 x86_64 Linux，或 WSL2 的 Linux 文件系统，以及可用的 Docker Engine、Git 和 Python 3。在仓库根目录执行：

```sh
./scripts/qemu.sh prepare
./scripts/qemu.sh validate
```

`prepare` 创建构建容器，编译官方 Xen 和同一提交的 C 工具栈，生成 Debian ARM64 根文件系统、内核和 initramfs，最后导出 Dom0 与 guest1 的 ext4 磁盘。`validate` 使用 QEMU TCG 仿真执行，无需 `/dev/kvm`、实体 Pi4 或在宿主挂载目标磁盘。首次准备需要联网获取 Docker 镜像、官方 Xen/PRoot 源码和 Debian/Ubuntu 软件包，保留 HTTPS 证书和软件包签名校验。

准备结果放在 `local/qemu/`：`xen`、`Image`、`initrd.img`、`dom0.ext4` 和 `guest1.ext4`。Dom0 磁盘为 4 GiB，guest 磁盘为 1.5 GiB，guest 磁盘还会嵌入 Dom0 磁盘中。构建容器、源码、展开的文件系统和临时文件需要额外空间。生成的磁盘不纳入 Git；仓库提供构建脚本与已执行的验证证据。

已有产物时，`validate` 直接复用它们；修改构建配置或目标脚本后先重新执行 `prepare`。每次运行的结果保存于 `local/qemu/results/<UTC时间>/`，汇总命令日志在 `local/qemu/logs/validation.log`。成功时脚本退出码为 0，`report.json` 的总状态及各项检查均为 `PASS`；失败时保留原始输出和已完成的检查，未到达的步骤标为 `NOT_RUN`。

## 实际验证平台

| 组件 | 本次运行配置 |
| --- | --- |
| QEMU | Ubuntu 22.04 的 QEMU 6.2.0，`qemu-system-aarch64`，TCG |
| 机器 / CPU | `virt,gic-version=3,virtualization=on`，Cortex-A57，2 个 CPU |
| 内存 | 总计 1536 MiB；Dom0 512 MiB；guest1 256 MiB、1 vCPU |
| Xen 与 C 工具栈 | 官方 4.19.0，同一提交 `026c9fa29716b0ff0f8b7c687908e71ba29cf239` |
| Dom0 / guest Linux | Debian bookworm ARM64，Linux 6.1.190（包名 `6.1.0-54-arm64`） |
| Dom0 设备 | virtio 块设备、virtio 网卡、Xen hvc0 控制台 |
| guest 设备 | Xen PV 块设备 `xvda` 和 hvc0 控制台 |
| SSH | QEMU user networking 转发本地随机端口至 Dom0 22；使用仓库实验公钥 |
| 管理工具 | 仓库 `scripts/target/guest1-start`、`guest1-counter`、`guest1-pause-demo` |

设备树由运行时 QEMU 导出后加入 Xen 启动参数及 Dom0 内核、initramfs 模块信息。QEMU 直接加载 Xen，Xen 再启动 Dom0。验证镜像的 Dom0 与 guest 控制台都自动登录 root；SSH 使用公钥。Pi4 镜像的 Dom0 串口密码登录设置与此不同。

Xen 源码和 PRoot 源码提交、Debian 基础容器摘要固定在脚本中；Debian/Ubuntu 软件包从受签名校验的仓库解析。本次具体包版本由 `rootfs-packages.tsv` 记录。未来重新构建可能获取更新的软件包，因此这里提供的是可重复执行的验证流程，不承诺逐字节相同的镜像。

## 自动检查内容

1. 观察实际 Xen 4.19.0 启动输出，进入 Dom0 root shell。
2. 执行 `xl info`、`xl list`、`xl dmesg`；确认起初仅有 Domain-0，没有自动启动 guest1。
3. 用 `guest1-start --console` 手动创建 guest，检查 `hostname`、`uname -m`，向 `/root/qemu-write-test` 写入内容并 `sync`，再从控制台退回 Dom0。
4. 从仿真器所在容器通过真实 SSH 公钥认证进入 Dom0，再用 `xl console guest1` 连接已有 guest 的控制台。
5. 在 guest 中运行有限计数，暂停 guest，检查暂停状态与计数停止，并确认 Dom0 仍能执行命令；恢复后检查计数继续。
6. 执行项目的 `guest1-pause-demo 1`，确认恢复后 UUID 不变，guest shell 仍可用。这是功能验证，不测量精确调度延迟。
7. 正常关闭 guest，确认 domain 消失；重新创建 guest，读取此前写入的文件，验证根文件系统持久化，再正常关机。
8. QEMU 退出后，重新计算原始 Dom0 磁盘 SHA256，确认 `-snapshot` 临时覆盖层没有改动源磁盘。

每个目标命令的输出和退出码记录于 `report.json`；完整串口输出保存于 `serial.log`，SSH 与 guest 控制台输出保存于 `ssh-guest-console.log`。报告同时记录 QEMU 版本、完整启动参数及 Xen、内核、initramfs、Dom0 磁盘的 SHA256。最终 guest 正常关机后，控制器结束仿真进程；这不代表执行了 Dom0 的关机流程。

## 仓库中的运行证据

本轮完整记录已归档在 `evidence/qemu/20261028/`：

- [逐项结果与目标命令退出码](evidence/qemu/20261028/report.json)。
- [完整串口日志](evidence/qemu/20261028/serial.log)。
- [Dom0 SSH 与 guest 控制台日志](evidence/qemu/20261028/ssh-guest-console.log)。
- [49 项辅助工具测试](evidence/qemu/20261028/helper-tests.log)。

## 范围与尚未完成项

这套验证实际运行 Xen、Dom0、guest1 和项目管理脚本。它使用独立的 Debian 验证镜像；Pi4 Yocto layer 的完整解析、构建与整卡产物检查仍受官方 `git.yoctoproject.org` 访问阻塞。QEMU 成功不能替代这些构建结果。

本次机器是通用 ARM `virt`，不是 `raspi4b`。没有执行 Pi 固件 → U-Boot → Xen 的实体启动链，也没有验证 Pi4 设备树、SD 卡或 GENET 网卡。Pi4 上板启动与 SSH 仍需真实镜像和板卡日志。当前没有可烧录的 Pi4 `.img`。

本阶段只做基础功能；TEE、安全启动与加密服务需在基础交付后收到下一步指令再开始。
