# QEMU validation scope

QEMU 可以验证 Xen、Dom0 和 guest1 的运行功能，但本工程目前没有完成一次 QEMU 系统启动。工具单元测试、文件系统读取测试和构建容器成功，都不是 Xen 启动成功的证据。

## 两种机器模型

| 方式 | 能覆盖的内容 | 不能据此宣称通过的内容 |
| --- | --- | --- |
| `qemu-system-aarch64 -machine virt,virtualization=on` | 构建匹配的镜像后，可检查 Xen 启动、Dom0 工具栈、Guest 虚拟块设备、hvc0 shell、暂停恢复、重复创建；配置虚拟网络后可测 Dom0 SSH | Pi 固件、Pi4 U-Boot 配置、真实 SD/eMMC、Pi4 设备树、GENET 网卡与真实板卡启动 |
| `qemu-system-aarch64 -machine raspi4b` | 支持该机器的 QEMU 版本提供 Cortex-A72、串口、SD/MMC、GIC 等模型，可作为 Pi4 相关驱动和启动实验的补充 | 不能假定完整复现实体 Pi4；未实现的外设和不同固件入口会限制验证 |

QEMU 官方 v10.0.0 文档列出 `raspi4b` 为四核 Cortex-A72、2 GiB 内存模型，并明确列出 **Pi4 PCIe Root Port 和 GENET Ethernet Controller 尚未实现**。对应实现还会从输入 DTB 中移除不支持的 PCIe、GENET 等节点。因此，不能用该模型中的 SSH 或虚拟网卡结果证明实体 Pi4 的 GENET 以太网已正常工作。

也不能笼统地说 QEMU 的 Pi4 模型没有虚拟化支持：v10.0.0 的 BCM2838 模型启用了 GIC400 virtualization extensions，并连接了 EL2 和虚拟定时器中断。通用 ARM64 内核加载路径在 CPU 具备 EL2 时选择 Non-secure EL2 入口。这些源码事实说明可以研究直接加载 Xen；它们本身不构成此工程已经启动 Xen 的证据。

使用 QEMU 的 `-kernel` 或模拟器固件加载接口，可能绕过真实 Pi 上的 VideoCore 固件启动步骤。不能把这样的成功日志写成“Pi 固件 → U-Boot → Xen”整条实体启动链已验证。

## 本项目推荐的验证路径

优先建立与 Pi4 输出隔离的 `qemuarm64` / `virt` 构建，以验证通用 Xen 功能，再进行 Pi4 上板验证。

当前 `pi4-xen` distro 和外层 image 是 Pi4 专用的：选择了 Pi4 DTB、Pi4 U-Boot 脚本及 SD 卡 Wic 布局。不能只把现有 `MACHINE` 改成 `qemuarm64`，便认为已经得到可运行的 QEMU 配置。

后续实现需要：

1. 独立的 QEMU 构建目录及配置，保留现有 Pi4 配置和产物。
2. `MACHINE = "qemuarm64"`，使用与 `virt` 匹配的 Linux BSP，核对 Xen 支持、GICv3、实际选用的 virtio 块设备和网卡驱动；不要继承 Pi4 专用 DTB 与启动脚本。
3. 复用 `guest1` 的配置、rootfs 打包方式和管理工具，但构建适合该机器的 Xen、Dom0 内核、Dom0 rootfs 和 Guest 内核。
4. 使用 meta-virtualization 的 `qemuboot-xen-defaults`、`qemuboot-xen-dtb`，为 Xen 生成含 Dom0 kernel module 的 DTB，并启用 `virtualization=on`。上游 `xen-image-minimal` 展示了这些类的实际用法。
5. 分配足够内存覆盖 Xen、512 MiB Dom0 和 256 MiB guest1；上游默认的 512 MiB QEMU 总内存和 192 MiB Dom0 不能原样当成本项目的预算。
6. 实际启动并保留终端日志，验证 `xl info`、`xl list`、`xl dmesg`、`guest1-start --console`、guest shell/可写根文件系统、`guest1-pause-demo` 和再次创建。SSH 需要额外记录真实连接结果。

上游 `qemuboot-xen-defaults.bbclass` 已使用 `virt,gic-version=3` 和 `virtualization=true`；`qemuboot-xen-dtb.bbclass` 会从 QEMU 导出的设备树构造 Xen 参数及 Dom0 内核模块信息。应复用这套机制，避免把没有 Xen 模块信息的普通 QEMU DTB 直接交给 Xen。

## 当前验证状态

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| QEMU 可行性和上游支持核对 | PASS | 已核对下列官方 QEMU 源码和现有 meta-virtualization 源码 |
| QEMU 专用构建配置及目标产物 | NOT_RUN | 尚未实现、构建对应目标；当前正式 Yocto layer 获取仍有网络阻塞 |
| QEMU Xen → Dom0 启动 | NOT_RUN | 没有相应系统启动日志 |
| QEMU guest1 shell、暂停恢复、重复创建 | NOT_RUN | 没有运行中的 Xen/Dom0/Guest 系统 |
| Pi4 实机验证 | NOT_RUN | QEMU 结果不能替代此项 |

2026-10-28 调查时，宿主和现有 `pi4-xen-build:scarthgap` 容器中均未找到 `qemu-system-aarch64`。即使随后安装了 QEMU，也必须完成匹配镜像构建和实际启动，才能更新上述运行验证状态。

## 源码依据

- [QEMU v10.0.0 Raspberry Pi 文档](https://github.com/qemu/qemu/blob/v10.0.0/docs/system/arm/raspi.rst)
- [BCM2838 GIC 与 CPU 模型](https://github.com/qemu/qemu/blob/v10.0.0/hw/arm/bcm2838.c)
- [raspi4b DTB 修改和缺失外设处理](https://github.com/qemu/qemu/blob/v10.0.0/hw/arm/raspi4b.c)
- [ARM 内核加载与 EL2 入口处理](https://github.com/qemu/qemu/blob/v10.0.0/hw/arm/boot.c)
- [QEMU virt 机器的 virtualization 开关](https://github.com/qemu/qemu/blob/v10.0.0/docs/system/arm/virt.rst)
- meta-virtualization commit 候选 `6e8e75775f1c73c7d5e8ffa9b1eb6040f7d10819` 的 `classes/qemuboot-xen-defaults.bbclass`、`classes/qemuboot-xen-dtb.bbclass` 和 `recipes-extended/images/xen-image-minimal.bb`。本次可读调查副本与正式官方检出的区别见 `STATUS.md`。

本文件说明基础功能验证，不引入 TEE、安全启动或加密服务。
