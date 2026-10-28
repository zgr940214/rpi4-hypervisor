# Status and evidence

日期：2026-10-28。范围：Pi4 AArch64、Xen、Dom0 和单个 `guest1`。用户明确要求在基础版交付并收到下一步指令后才开始 TEE/安全工作，本工程未启用这些功能。

## 当前结论

**当前交付目标是 Yocto 从源码构建 Pi4 的 Xen、Dom0 和 guest1，并将它们一起打包、验证。完整镜像构建尚未完成，当前没有可烧录产物。** `git.yoctoproject.org/meta-virtualization` 的源码拉取仍被云环境代理返回 CONNECT 403；[本次访问记录](evidence/yocto-source-build/20261028/source-access.log)。这是构建配方源码的访问问题，不是预制 OS 镜像下载。

已实现同一构建的 guest/内核打包、来源记录与字节一致性校验，以及直接使用完整 Pi4 `.img` 的 QEMU 入口。先前 Debian QEMU 实验的真实通过记录仍保留，但不属于本次 Yocto 自建 Pi4 镜像验收。详见 [QEMU 验证说明](QEMU.md)。

| 检查 | 状态 | 证据或原因 |
| --- | --- | --- |
| Ubuntu 构建容器 | PASS | `evidence/container-build.log`，实际 Docker 构建成功；重复构建退出码 0 |
| 管理、凭据、镜像及构建来源检查工具 | PASS | [本次记录](evidence/yocto-source-build/20261028/tool-tests.log)，69 项通过、0 跳过，退出码 0；包含替换 guest、来源不一致及旧检查结果的拒绝路径，仍属于工具测试 |
| 正式 Poky、meta-openembedded、meta-raspberrypi 固定检出 | PASS | `evidence/bootstrap-host.log`，前 3 个 lock commit 已取得 |
| 官方 meta-virtualization 固定检出 | BLOCKED | [实际源码访问](evidence/yocto-source-build/20261028/source-access.log)仍为 HTTPS CONNECT 403 |
| 隔离离线配方解析 | PASS（仅诊断） | [记录](evidence/yocto-source-build/20261028/offline-parse.log)：2939 recipes、4885 targets、687 skipped、0 errors。使用已有研究 layer，未验证官方来源，不是正式构建通过 |
| 隔离离线任务图 | PASS（仅诊断） | [记录](evidence/yocto-source-build/20261028/offline-taskgraph.log)：286 recipes；确认 guest 镜像与共享内核是 Dom0 打包依赖 |
| 正式 BitBake 解析与源码版本核对 | BLOCKED | 等待官方 layer 获取；Pi4 内核分支与 SRCREV 对应关系仍需核实 |
| Yocto Pi4 整卡编译 | BLOCKED | 未完成正式源码获取，尚未执行整卡编译任务 |
| 自建整卡静态检查 | NOT_RUN | 没有 `.wic`/`.img`；合成测试文件不能充当交付镜像 |
| 自建整卡 QEMU 启动及 guest 验证 | NOT_RUN | [新入口实际拒绝记录](evidence/yocto-source-build/20261028/qemu-required-image.log)：缺少自建 Pi4 镜像时退出码 1，不替换为 Debian |
| Pi4 实机启动与运行验证 | NOT_RUN | 尚无构建镜像与已连接板卡 |
| 历史 Debian QEMU 实验 | PASS（独立实验） | [报告](evidence/qemu/20261028/report.json)：10/10 项、31/31 条命令通过；不是 Yocto Pi4 镜像 |

此前的干净 Git 检出测试为提交 `a63c6316c8a0455a874ab3f4ec03af15e1e113fb` 的 47 项测试，记录于 `evidence/clean-checkout-test.log`。云安装脚本演练的 46 项与后续 49 项工具测试各自对应原始提交与日志，不作为当前新增逻辑的测试数量。

## 工程起点与选择

开始任务时仓库为无提交空仓库，远程未提供分支，没有原有成功配置或产物可以复用。当前工程在 `/workspace/rpi4-hypervisor` 从零建立，未创建 worktree。

容器把仓库根目录映射到 `/work`。宿主是 x86_64 Debian 13；实际构建宿主采用 Ubuntu 22.04，CPU cgroup 配额约 4 核、内存限制 32 GiB；准备开始时工作盘可用约 30 GiB，容器和源码准备后约 28 GiB。没有发现既有 downloads/sstate 缓存。

下表为当前配置。隔离离线审计确认了候选 provider 和任务图；该审计使用本地研究 layer，不能代替官方源码检出和正式构建。成功构建后，实际 provider、版本和源码信息会导出到 `artifacts/versions.json`。

| 项目 | 配置 |
| --- | --- |
| Yocto | Scarthgap，layer commit 固定在 `sources.lock.json` |
| MACHINE / DISTRO | `raspberrypi4-64` / `pi4-xen` |
| Dom0 image | `pi4-xen-dom0-image` |
| Guest image | `pi4-guest1-image`，独立无分区 ext4，复用同一份 ARM64 内核 |
| Linux | `linux-yocto` 6.6；固定 Poky recipe 当前标识 6.6.151 |
| Linux Pi4 BSP | `v6.6/standard/bcm-2xxx-rpi` / `bcm-2xxx-rpi4`，需取得官方源码后核对 recipe SRCREV 与分支关系 |
| Xen / xen-tools | 上游 4.19.0；recipe PV 分别为 `4.19.0+stable` 和 `4.19+stable` |
| Xen source | 官方 `xen-project/xen` commit `026c9fa29716b0ff0f8b7c687908e71ba29cf239` |
| U-Boot | 2024.01，Pi4 ARM64，复用 `xen-rpi-u-boot-scr` recipe 并替换脚本模板 |
| 内存 / vCPU | Dom0 512 MiB、guest1 256 MiB / 1 vCPU，集中于 distro 配置 |
| 磁盘 | Wic MBR：FAT 启动分区 + ext4 Dom0；guest ext4 存放于 Dom0 的 `/var/lib/xen/images/guest1/` |
| 登录 | Dom0 root SSH 公钥与串口密码；guest hvc0 本地自动进入 root shell |

`meta-virtualization` 候选 commit 来自先前的 scarthgap 研究 clone。本次仅在独立 scratch 配置中使用该已有 clone 做离线审计，容器 `--network none`，BitBake `BB_NO_NETWORK=1`；未替换正式源码目录，也未用它构建交付镜像。正式获取脚本仍要求 `https://git.yoctoproject.org/meta-virtualization` 的固定提交。

离线审计还发现：Pi4 覆盖层设置 `KBRANCH=v6.6/standard/bcm-2xxx-rpi`，而 `SRCREV_machine` 沿用 Poky 默认值。获取权威内核源码后，需要核实提交与 Pi4 分支的关系，不能只凭拉取成功推断 BSP 正确。

## 实现内容

- `sources.lock.json`、`container/` 和 `scripts/{bootstrap,init-build,configure-access,...}`：固定源版本、Ubuntu 构建环境、可重复配置、凭据生成、日志及退出状态。
- `meta-pi4-xen-lab/`：同一 Yocto 工程构建两个 image、共享内核、Xen/U-Boot 与最终 Wic。guest 打包任务依赖真实的 guest image 完成和 kernel deploy；两个根文件系统带 Yocto 构建标记，guest 包携带包清单、内核来源和载荷哈希。
- `scripts/target/`：避免重复创建 guest、有限计数及带清理逻辑的暂停恢复。采用 domain ID 和 UUID 联合核对；CLI 检查与操作仍要求没有其他并发 domain 管理者。
- `scripts/check-image.py`、`export-image.py`：导出字节一致的整卡 `.img`，校验内嵌 guest 磁盘、共享内核和包清单与实际 BitBake 部署输出一致，核对启动分区 Xen/内核，并生成版本与 SHA256 证据。
- `tests/`：运行工具错误路径和真实文件系统读取测试；不把合成测试产物当作启动镜像。
- `scripts/qemu-yocto.sh`、`scripts/qemu/prepare-yocto.py`：验证自建 Pi4 整卡来源，提取该卡原有 Xen/内核，把完整原卡直接作为 QEMU 磁盘；内嵌 guest 不替换。
- `scripts/qemu.sh`：仅保留此前独立 Debian 实验的复现入口，不作为自建 Pi4 镜像验收入口。

## 仓库交付

用户要求直接拉取仓库，因此工程、上述 evidence 原始记录及 `local/credentials/` 中的四个实验凭据文件纳入 Git。首次准备会修复 Git 检出导致的私钥权限变化并验证凭据配对关系。缓存、构建输出和生成的本地配置继续忽略。

## 恢复构建所需动作

环境网络配置草稿已保存 Yocto layer、内核、工具链和用户空间源码所需的域名，包括 `git.yoctoproject.org`、`downloads.yoctoproject.org`、GNU、Kernel.org、U-Boot 等上游站点及 Pi 固件使用的 GitHub API。当前运行时仍未应用这些增补。需要在环境设置中保存网络配置；保存草稿本身不会改变运行中的访问权限。源码重定向或后续依赖若出现新的明确拒绝，再按实际 URL 补充。

已保存并确认持久化的字段为 `network.allowed_domains`、`install_script` 和 `start_skill`。安装脚本的内容已在当前实例实际演练；保存配置不等于已应用网络设置或已发布新快照，未来任务恢复尚未验证。

网络生效后，从仓库根目录继续：

```sh
./scripts/container.sh prepare
./scripts/container.sh parse
./scripts/container.sh plan
./scripts/container.sh build
./scripts/qemu-yocto.sh validate
```

先核对官方 layer commit、Pi4 内核分支与 SRCREV、解析出的 provider 和任务图，再执行全量构建。构建流程获取源码、构建支持工具及 Pi 必需启动固件，不下载预制 guest OS 镜像。保留 TLS、签名与校验和验证。当前工作盘可用空间约 18 GiB，实际编译峰值尚未测出；保留 `rm_work` 与磁盘低空间监控，不能宣称现有容量已验证足够，也不删除已有下载缓存来绕过空间问题。

预期烧录文件为 `artifacts/pi4-xen-dom0-guest1.img`，校验值为 `artifacts/SHA256SUMS`；**当前两个文件都尚未生成**。烧录与上板步骤见仓库 README，只有执行并保留真实日志后才能将对应状态改为 PASS。
