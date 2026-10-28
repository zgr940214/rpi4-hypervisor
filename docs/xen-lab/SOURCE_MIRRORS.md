# 源码镜像与复现

本工程用 Yocto 编译 Xen、Pi4 内核、Dom0 和 guest1。镜像源提供构建配方和软件源码；Debian/Ubuntu 的 `.orig.tar.*` 是源码包。下面记录源码选择、校验和复现方法。完整镜像构建与自建镜像 QEMU 验证仍在进行，最终结果见 [STATUS.md](STATUS.md)；这里的源码或独立 bootstrap 检查不能代替这些结果。

新克隆仓库后，直接使用 [README](../../README.md) 的正常入口：

```sh
./scripts/container.sh build-container
./scripts/container.sh prepare
./scripts/container.sh parse
./scripts/container.sh plan
./scripts/container.sh build
```

`prepare` 按 [sources.lock.json](../../sources.lock.json) 检出固定提交的 layers，包括 meta-virtualization 的备用 Git 地址。[layer.conf](../../meta-pi4-xen-lab/conf/layer.conf) 自动加载 Git 镜像、压缩包镜像和 URI 替换类；各软件的源码变体写在 layer 内的 `.bbappend`。构建脚本生成的配置还加载 [build-host.inc](../../meta-pi4-xen-lab/conf/build-host.inc)。这些设置都随仓库保存，新克隆无需复制本次会话的 `.cache/`、临时配置或 `local/site.conf`，也无需手工修改 upstream layer。

源码选择有以下几种情况：

| 情况 | 仓库中的实现与校验 |
| --- | --- |
| 同一 Git 提交的镜像 | [source-mirrors.inc](../../meta-pi4-xen-lab/conf/source-mirrors.inc) 使用 `PREMIRRORS` 将原站映射到 HTTPS Git 镜像；配方的固定 `SRCREV` 和分支要求继续生效。[镜像解析记录](evidence/source-mirrors/20261028/pinned-sources/git-premirror-resolution.json)列出实际映射。 |
| 字节完全相同的压缩包 | [archive-mirrors.inc](../../meta-pi4-xen-lab/conf/archive-mirrors.inc) 保存原 URL 与镜像 URL 对应关系。[pi4-source-mirrors.bbclass](../../meta-pi4-xen-lab/classes/pi4-source-mirrors.bbclass) 替换 URI，并用 `downloadfilename` 保留原缓存文件名及 URI 参数。镜像可以使用 Debian 的不同文件名，原配方 SHA256 仍须完全匹配。[证据](evidence/source-mirrors/20261028/archive-mirrors.json)包含对应 URL 与摘要。 |
| 同版本的另一种源码归档 | `.bbappend` 明确选择新的归档 URI、文件名和经过独立验证的摘要。M4 的 XZ 包有 [GNU 签名与独立摘要](evidence/source-mirrors/20261028/m4/verification.json)；Automake、Patch、Libtool 等有 [Debian 签名索引链](evidence/source-mirrors/20261028/gnu-xz/README.md)，Bash、lzlib 有 [Ubuntu 签名索引链](evidence/source-mirrors/20261028/ubuntu-gnu/README.md)。这些是明确的源码选择变更，不能声称匹配旧 gzip 包摘要。 |
| 同版本的上游 Git 发布源码 | `.bbappend` 使用发布标签对应的固定 commit；需要子模块时同时固定其 commit。Git 检出缺少的发布包生成文件由配方生成。参见 [Autoconf](evidence/source-mirrors/20261028/autoconf/source.json)、[Gawk](evidence/source-mirrors/20261028/git-source/gawk.json)及其他 [固定源码记录](evidence/source-mirrors/20261028/pinned-sources/)。Git 源码由 commit 固定，旧归档摘要不用于证明 Git 工作树。 |
| 明确的发行版源码重打包 | Gperf 3.1 采用签名索引认证的 Debian Git 源码归档，并使用独立文件名。Tar 1.35 采用 `+dfsg` 源码包：移除 info 手册、保留 man 页面，并调整文档构建规则；版本、许可证和原配方补丁保留。[Tar 证据](evidence/source-mirrors/20261028/tar/verification.json)包含重打包脚本及与上游标签的 35 个运行时源码文件逐字节比较结果。 |

GMP 6.3.0 的 XZ 包还有更强的[源码一致性证明](evidence/source-mirrors/20261028/gmp/original-identity-proof.json)：解压后用 bzip2 级别 9 压缩，得到原配方要求的完整 `.tar.bz2` SHA256。当前配方直接下载固定镜像提交中的 XZ 文件，新克隆无需先运行转换脚本。

Pi4 内核分支与版本另由 [linux-yocto_6.6.bbappend](../../meta-pi4-xen-lab/recipes-kernel/linux/linux-yocto_6.6.bbappend) 显式固定为 Pi4 BSP 的 `6.6.100` 提交。分支、版本和提交均在该文件中单独记录。

[Dockerfile](../../container/Dockerfile) 固定 Ubuntu 22.04 基础镜像摘要，并安装构建宿主工具。Autoconf、Gettext 等 Git 发布源码需要生成 `configure`、`Makefile.in` 或导入 gnulib；配方明确调用该宿主的 Autoconf、Automake、M4、Perl 等工具，随后继续执行原配方补丁及 Yocto 构建。Autoconf-archive 只安装固定源码中的完整 M4 宏集合和许可证，不生成可选手册。目标工具链及目标 libc 仍由 Yocto 编译。

宿主配置关闭 `uninative`，避免依赖原站的预编译宿主兼容包。M4、Automake、Libtool、Patch 的早期 native 任务用 [host-xz-bootstrap.inc](../../meta-pi4-xen-lab/recipes-devtools/host-xz-bootstrap.inc) 中固定的 `/usr/bin/xz` 解压，打破它们与 `xz-native` 的循环依赖；只移除这几个 native 配方的解压依赖，其他 `xz-native`/liblzma 构建依赖保留。

Gettext 0.22.5 的 Git 源码与它记录的 gnulib 提交共同生成发布文件。`autopoint` 所需的历史宏归档另从经过 Debian 签名索引认证的 Gettext 0.23.1 源码包中提取，仅使用 `archive.dir.tar`，并核对内层摘要及其中 0.22.5 快照的全部 22 个文件；不编译或安装 0.23.1 的程序。配方跳过 Git 检出中缺少发布生成文件的可选手册与示例，保留程序、库、普通翻译目录、宏、autopoint 和测试。详细记录见 [gettext-history](evidence/source-mirrors/20261028/gettext-history/)。

可导出当前实际选中配方的源码清单，随后按需预取备用压缩包：

```sh
./scripts/container.sh sources
python3 scripts/mirror-sources.py
```

`sources` 在构建容器内生成任务图，再由 [source-manifest.py](../../scripts/source-manifest.py) 导出展开后的 URL、固定提交、下载路径及摘要到 `local/source-manifest.json`。[mirror-sources.py](../../scripts/mirror-sources.py) 是可选缓存辅助工具，只有下载字节匹配清单中的 SHA256 才会写入 `.cache/downloads/`；现有缓存摘要不符时会报错并保留原文件。结果写入 `local/source-mirrors.json`。它沿用正常代理和证书校验，在托管云环境中只尝试允许的源站或镜像域名。

验证结果必须按范围读取：[源码证据目录](evidence/source-mirrors/20261028/)中的标签、签名、许可证、补丁及离线 bootstrap/native 编译记录，只证明各自记录的检查。例如 Autoconf 的独立编译通过，不代表完整 BitBake 构建通过。正式构建任务、镜像导出和 QEMU 验证分别查看 `local/logs/`、[STATUS.md](STATUS.md) 与 [QEMU.md](QEMU.md)；完整交付需要实际整卡产物和对该产物的运行记录。
