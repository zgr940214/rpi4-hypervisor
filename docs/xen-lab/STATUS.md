# Status and evidence

日期：2026-10-28。范围：Pi4 AArch64、Xen、Dom0 和单个 `guest1`。用户明确要求在基础版交付并收到下一步指令后才开始 TEE/安全工作，本工程未启用这些功能。

## 当前结论

**基础工程和构建容器已建立；完整镜像构建被官方源站访问权限阻塞，尚无可烧录产物。**

| 检查 | 状态 | 证据或原因 |
| --- | --- | --- |
| Ubuntu 构建容器 | PASS | `docs/xen-lab/evidence/container-build.log`，实际 Docker 构建成功 |
| 容器重复构建 | PASS | `docs/xen-lab/evidence/container-repeat.log`，缓存复用、退出码 0 |
| 目标管理、凭据和镜像检查工具测试 | PASS | `docs/xen-lab/evidence/tool-tests.log`，47 项执行、0 失败、0 跳过，退出码 0 |
| layer 词法及内嵌 Python 静态检查 | PASS | `docs/xen-lab/evidence/layer-static-check.log`，14 个 metadata 文件；不等同于完整 BitBake 解析 |
| 保存的云安装脚本演练 | PASS | `docs/xen-lab/evidence/cloud-install.log`，容器缓存复用、凭据复用和 46 项测试通过 |
| 凭据生成和复用 | PASS | 本地检查确认重复运行不改变凭据、公私钥匹配、密码与 SHA512 哈希匹配、文件权限 0600；不记录秘密内容 |
| Poky、meta-openembedded、meta-raspberrypi 固定检出 | PASS | `docs/xen-lab/evidence/bootstrap-host.log`，前 3 个 lock commit 已取得 |
| 官方 meta-virtualization 固定检出 | BLOCKED | 同上及 `docs/xen-lab/evidence/dependency-prepare.log`，HTTPS CONNECT 被平台代理返回 403 |
| 完整 BitBake 解析/provider 和任务图 | BLOCKED | 缺少上述正式 layer，尚未运行完整解析 |
| 目标整卡构建 | BLOCKED | 前置依赖获取失败；未启动 BitBake 编译任务，不能报告构建通过 |
| 真实镜像静态检查 | NOT_RUN | 尚未生成 `.wic`/`.img`；工具的测试镜像不代表交付镜像 |
| QEMU 系统启动 | NOT_RUN | 尚无匹配的仿真镜像和系统启动日志，详见 `QEMU.md` |
| Pi4 实机启动、Dom0 SSH、guest shell、暂停恢复及重复创建 | NOT_RUN | 没有已连接的板卡，也尚无镜像 |

## 工程起点与选择

开始任务时仓库为无提交空仓库，远程未提供分支，没有原有成功配置或产物可以复用。当前工程在 `/workspace/rpi4-hypervisor` 从零建立，未创建 worktree。

容器把仓库根目录映射到 `/work`。宿主是 x86_64 Debian 13；实际构建宿主采用 Ubuntu 22.04，CPU cgroup 配额约 4 核、内存限制 32 GiB；准备开始时工作盘可用约 30 GiB，容器和源码准备后约 28 GiB。没有发现既有 downloads/sstate 缓存。

下表是配置意图，**不是完整 BitBake 解析后证实的 provider 结果**。正式 provider 和版本将在成功构建后导出到 `artifacts/versions.json`。

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

`meta-virtualization` 候选 commit 来自一个可读取的第三方 scarthgap 镜像，用于源码调查。正式获取脚本只接受 `https://git.yoctoproject.org/meta-virtualization`，未把第三方镜像当作已验证的官方检出。官方 commit 校验仍是上述阻塞的一部分。

## 实现内容

- `sources.lock.json`、`container/` 和 `scripts/{bootstrap,init-build,configure-access,...}`：固定源版本、Ubuntu 构建环境、可重复配置、凭据生成、日志及退出状态。
- `meta-pi4-xen-lab/`：小型自定义 layer、集中资源参数、两个 image、内核片段与最终配置检查、启动脚本、Xen 管理服务、SSH/DHCP、Guest 打包任务依赖。
- `scripts/target/`：避免重复创建 guest、有限计数及带清理逻辑的暂停恢复。采用 domain ID 和 UUID 联合核对；CLI 检查与操作仍要求没有其他并发 domain 管理者。
- `scripts/check-image.py`、`export-image.py`：成功构建后导出字节一致的 raw `.img`，进行只读结构/文件/配置检查并生成版本与 SHA256 证据。
- `tests/`：运行工具错误路径和真实文件系统读取测试；不把合成测试产物当作启动镜像。

## 仓库交付

用户要求直接拉取仓库，因此工程、上述 evidence 原始记录及 `local/credentials/` 中的四个实验凭据文件纳入 Git。首次准备会修复 Git 检出导致的私钥权限变化并验证凭据配对关系。缓存、构建输出和生成的本地配置继续忽略。

## 恢复构建所需动作

环境网络配置草稿已增加 `git.yoctoproject.org`、`downloads.yoctoproject.org` 和 `sstate.yoctoproject.org`，但当前运行时仍为原来的网络列表。需要在环境设置中保存更改；配置与快照发布由产品界面完成。

已保存并确认持久化的字段为 `network.allowed_domains`、`install_script` 和 `start_skill`。安装脚本的内容已在当前实例实际演练；保存配置不等于已应用网络设置或已发布新快照，未来任务恢复尚未验证。

网络生效后，从仓库根目录继续：

```sh
./scripts/container.sh prepare
./scripts/container.sh parse
./scripts/container.sh plan
./scripts/container.sh build
```

先核对官方 layer commit、Pi4 内核分支与 SRCREV、解析出的 provider 和任务图，再执行全量构建。若 BitBake 下载其他上游依赖遇到具体拒绝，应根据失败 URL 补充对应域名，保留 TLS/校验和验证。工作盘容量的实际构建峰值尚未测出；监控低空间阈值，不删除已有缓存来绕过空间问题。

预期烧录文件为 `artifacts/pi4-xen-dom0-guest1.img`，校验值为 `artifacts/SHA256SUMS`；**当前两个文件都尚未生成**。烧录与上板步骤见仓库 README，只有执行并保留真实日志后才能将对应状态改为 PASS。
