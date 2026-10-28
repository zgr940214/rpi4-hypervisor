# Status and evidence

日期：2026-10-28。范围：Pi4 AArch64、Xen、Dom0 和单个 `guest1`。用户明确要求在基础版交付并收到下一步指令后才开始 TEE/安全工作，本工程未启用这些功能。

## 当前结论

**Yocto 自建的 Pi4 Xen、Dom0 和 guest1 整卡镜像已完成，并通过对同一完整镜像的 QEMU 验证。** 最终镜像为 `1295329280` 字节，SHA256 为 `49fe88a3649b446cabcda7aa7c27ad81845bb950a3cfe602b0d057d5ab53e305`。仓库提供压缩分片，拉取后运行 `python3 scripts/repo-image.py restore` 即可得到 `artifacts/pi4-xen-dom0-guest1.img`。

2026-10-28 21:16:22–21:18:20（北京时间），本次 QEMU 运行完成 10/10 项检查、31/31 条目标命令，验证了 Dom0、guest shell、SSH、公钥登录后重新连接 guest 控制台、暂停恢复、正常关机、重新创建及磁盘写入保留。运行前后整卡哈希一致。Pi4 实机启动仍为 `NOT_RUN`；TEE/安全工作尚未开始。详见 [QEMU 验证说明](QEMU.md)。

| 检查 | 状态 | 证据或原因 |
| --- | --- | --- |
| Ubuntu 构建容器 | PASS | `evidence/container-build.log`，实际 Docker 构建成功；重复构建退出码 0 |
| 管理、凭据、镜像、构建来源与镜像下载工具 | PASS | [容器内记录](evidence/yocto-image/20261028/tool-tests.log)，99 项通过、0 跳过，退出码 0；包含镜像分片恢复工具测试 |
| 正式 Poky、meta-openembedded、meta-raspberrypi 固定检出 | PASS | `evidence/bootstrap-host.log`，前 3 个 lock commit 已取得 |
| meta-virtualization 固定检出 | PASS | [镜像与固定对象检查](evidence/source-mirrors/20261028/pinned-sources/layer-kernel-verification.json)；GitHub 镜像提供原 lock commit，重复 bootstrap 与严格 fsck 通过 |
| 隔离离线配方解析 | PASS（仅诊断） | [记录](evidence/yocto-source-build/20261028/offline-parse.log)：2939 recipes、4885 targets、687 skipped、0 errors。使用已有研究 layer，未验证官方来源，不是正式构建通过 |
| 隔离离线任务图 | PASS（仅诊断） | [记录](evidence/yocto-source-build/20261028/offline-taskgraph.log)：286 recipes；确认 guest 镜像与共享内核是 Dom0 打包依赖 |
| 正式 BitBake 解析与任务图 | PASS | [记录](evidence/source-mirrors/20261028/source-plan.log)：2939 recipes、4885 targets、0 errors；选中 232 个构建配方 |
| Pi4 内核源码与分支 | PASS | 实际 Pi4 分支提交 `0d5c8af531e021d38d2589c109268b644bdf3320`，源码版本 6.6.100；fsck、许可证和 Pi4 DTS 核对通过 |
| Yocto Pi4 整卡编译与导出 | PASS | [最终构建导出日志](evidence/yocto-image/20261028/build-export.log)，实际生成 `.wic` 和字节一致的 `.img`；交叉 GCC 13.5、glibc 2.39、Linux、Xen、工具栈及两个根文件系统均完成构建 |
| 自建整卡静态检查 | PASS | [报告](evidence/yocto-image/20261028/image-checks.json)：41 项 PASS、3 项 NOT_RUN，内嵌 guest、共享内核和启动载荷与部署产物匹配 |
| 自建整卡 QEMU 启动及 guest 验证 | PASS | [报告](evidence/yocto-image/20261028/report.json)：10/10 项、31/31 条目标命令成功；[来源记录](evidence/yocto-image/20261028/provenance.json)绑定上述最终镜像 |
| Pi4 实机启动与运行验证 | NOT_RUN | 尚未连接并运行实体 Pi4；无 Pi 固件 → U-Boot → Xen、实际 SD 卡和 GENET 网卡日志 |
| 历史 Debian QEMU 实验 | PASS（独立实验） | [报告](evidence/qemu/20261028/report.json)：10/10 项、31/31 条命令通过；不是 Yocto Pi4 镜像 |

静态报告中的三个 `NOT_RUN` 是 SSH 实际登录、Pi4 硬件启动及固件预留/EL2 入口；静态读取不能证明它们。其中 SSH 已由本次 QEMU 运行单独验证，硬件相关两项仍未验证。

此前的干净 Git 检出测试为提交 `a63c6316c8a0455a874ab3f4ec03af15e1e113fb` 的 47 项测试，记录于 `evidence/clean-checkout-test.log`。云安装脚本演练的 46 项、后续 49 项和 98 项工具测试各自对应原始提交与日志，不作为当前测试数量。

## 工程起点与选择

开始任务时仓库为无提交空仓库，远程未提供分支，没有原有成功配置或产物可以复用。当前工程在 `/workspace/rpi4-hypervisor` 从零建立，未创建 worktree。

容器把仓库根目录映射到 `/work`。宿主是 x86_64 Debian 13；实际构建宿主采用 Ubuntu 22.04，CPU cgroup 配额约 4 核、内存限制 32 GiB；准备开始时工作盘可用约 30 GiB，容器和源码准备后约 28 GiB。没有发现既有 downloads/sstate 缓存。

下表为当前配置。正式构建已使用镜像提供的固定 layer；实际 provider、版本和源码信息已导出到 [versions.json](evidence/yocto-image/20261028/versions.json)。最终[源码清单](evidence/yocto-image/20261028/source-manifest.json)包含 224 条源码记录，对应任务图选中的 232 个构建配方。

| 项目 | 配置 |
| --- | --- |
| Yocto | Scarthgap，layer commit 固定在 `sources.lock.json` |
| MACHINE / DISTRO | `raspberrypi4-64` / `pi4-xen` |
| Dom0 image | `pi4-xen-dom0-image` |
| Guest image | `pi4-guest1-image`，独立无分区 ext4，复用同一份 ARM64 内核 |
| Linux | `linux-yocto` 6.6.100，bbappend 明确覆盖版本与对应 Pi4 分支提交 |
| Linux Pi4 BSP | `v6.6/standard/bcm-2xxx-rpi` / `bcm-2xxx-rpi4`，从 Wind River 镜像取得真实分支，Pi4 DTS 与许可证已核对 |
| Xen / xen-tools | 上游 4.19.0；recipe PV 分别为 `4.19.0+stable` 和 `4.19+stable` |
| Xen source | 官方 `xen-project/xen` commit `026c9fa29716b0ff0f8b7c687908e71ba29cf239` |
| U-Boot | 2024.01，Pi4 ARM64，复用 `xen-rpi-u-boot-scr` recipe 并替换脚本模板 |
| 内存 / vCPU | Dom0 512 MiB、guest1 256 MiB / 1 vCPU，集中于 distro 配置 |
| 磁盘 | Wic MBR：FAT 启动分区 + ext4 Dom0；guest ext4 存放于 Dom0 的 `/var/lib/xen/images/guest1/` |
| 登录 | Dom0 root SSH 公钥与串口密码；guest hvc0 本地自动进入 root shell |

`meta-virtualization` 的规范来源仍记录为 `git.yoctoproject.org`，`sources.lock.json` 同时声明 GitHub 镜像。获取脚本核对原固定提交，拒绝脏目录、未知来源和不匹配的 HEAD。

此前 Pi4 覆盖层只改了 `KBRANCH`、沿用了 Poky 通用内核提交；现已同时固定实际 Pi4 分支提交和 6.6.100 版本。默认 6.6.151 标记不再被当作 Pi4 分支的实际版本。

## 实现内容

- `sources.lock.json`、`container/` 和 `scripts/{bootstrap,init-build,configure-access,...}`：固定源版本、Ubuntu 构建环境、可重复配置、凭据生成、日志及退出状态。
- `meta-pi4-xen-lab/`：同一 Yocto 工程构建两个 image、共享内核、Xen/U-Boot 与最终 Wic。guest 打包任务依赖真实的 guest image 完成和 kernel deploy；两个根文件系统带 Yocto 构建标记，guest 包携带包清单、内核来源和载荷哈希。
- `scripts/target/`：避免重复创建 guest、有限计数及带清理逻辑的暂停恢复。采用 domain ID 和 UUID 联合核对；CLI 检查与操作仍要求没有其他并发 domain 管理者。
- `scripts/check-image.py`、`export-image.py`：导出字节一致的整卡 `.img`，校验内嵌 guest 磁盘、共享内核和包清单与实际 BitBake 部署输出一致，核对启动分区 Xen/内核，并生成版本与 SHA256 证据。
- `tests/`：运行工具错误路径和真实文件系统读取测试；不把合成测试产物当作启动镜像。
- `scripts/qemu-yocto.sh`、`scripts/qemu/prepare-yocto.py`：验证自建 Pi4 整卡来源，提取该卡原有 Xen/内核，把完整原卡直接作为 QEMU 磁盘；内嵌 guest 不替换。
- `scripts/qemu.sh`：仅保留此前独立 Debian 实验的复现入口，不作为自建 Pi4 镜像验收入口。

## 仓库交付

用户要求直接拉取仓库，因此工程、上述 evidence 原始记录、`artifacts/repository-image/` 中的镜像分片与清单、运行复测所需的顶层 artifacts 元数据，以及 `local/credentials/` 中的四个实验凭据文件纳入 Git。`repo-image.py restore` 校验分片、完整压缩流和解压后的整卡摘要，恢复可烧录的 `.img`。原始 `.img`、编译目录、缓存和生成的本地配置继续忽略。

Git 不保留私钥的 `0600` 权限；准备脚本会修复权限并验证配对关系，直接使用 SSH 私钥前也可执行 `chmod 600 local/credentials/id_ed25519`。烧录步骤见 [README](../../README.md)。

## 已处理的问题与复现

当前镜像配置随仓库加载，无需依赖此前未应用的网络配置草稿。相同原包继续验证原 SHA256；Git 发布源码、另一压缩格式或 Debian 明确删去手册的 tar 源码，分别以 bbappend 和独立证据记录，不能宣称它们匹配原压缩包哈希。

容器宿主工具用于从 Git 生成发布文件；目标系统和交叉工具链由 Yocto 构建。未使用外部预构建 sstate。`rm_work` 和低空间监控保持启用；曾因约 32 GiB 工作盘不足停止一次，回收旧实验临时文件与闲置容器层后完成构建。源码缓存和成功任务保留；首次复现仍建议准备至少 100 GiB 可用空间，该值是规划建议，不是实测峰值。

实际集成中还修正了内核配置合并顺序：meta-virtualization 的后置片段把三个 Xen 驱动改成模块，最终片段重新要求内建，并保留配置断言。启动分区明确保留独立 `u-boot.bin` 与 Linux `Image`。静态读取使用构建对应的原生 e2fsprogs，支持生成的 ext4 特性。

第一次真实整卡 QEMU 运行成功进入 Dom0，但 Xen 拒绝 guest 磁盘配置：`target=` 置于开头时，其后的参数被解析为磁盘目标的一部分。失败报告与串口保留在 [initial/](evidence/yocto-image/20261028/initial/)，其中旧镜像 SHA256 与最终交付不同。修正参数顺序、用本次编译的 Xen 解析器确认配置、增强控制器对 guest 控制台的识别后，重新构建整卡并完成上述全部运行检查。初次失败未改写为 PASS。

从仓库根目录重新构建并验证：

```sh
./scripts/container.sh build-container
./scripts/container.sh prepare
./scripts/container.sh parse
./scripts/container.sh plan
./scripts/container.sh build
./scripts/qemu-yocto.sh validate
```

构建流程获取源码、构建支持工具及 Pi 必需启动固件，两个根文件系统均由 Yocto 生成。TLS、来源验证和许可证校验保留。若只需使用已验收的镜像，拉取仓库并运行恢复命令即可；实体板卡启动完成且保留实际日志后，再更新硬件验证状态。
