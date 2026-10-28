# Yocto 自建 Pi4 镜像工作记录

完整镜像构建仍为 BLOCKED，自建整卡 QEMU 为 NOT_RUN。本目录不包含可启动的 Pi4 镜像。

- `tool-tests.log`：实际构建容器运行 69 项工具测试，全部通过、0 跳过、退出码 0。包括替换 guest、伪装构建来源、旧报告和不匹配载荷的拒绝测试；这些测试使用合成数据，不代表系统启动。
- `source-access.log`：本轮执行 `git ls-remote https://git.yoctoproject.org/meta-virtualization refs/heads/scarthgap` 的原始输出，工具记录退出码 128，代理 CONNECT 403。拒绝发生在获取构建配方源码时，没有请求预制 OS 镜像。
- `qemu-required-image.log`：新入口实际因缺少自建 Pi4 整卡产物退出 1，没有自动使用历史 Debian 系统。
- `offline-parse.log`、`offline-taskgraph.log`、`audit-summary.json`、`pn-buildlist`、`offline-task-depends.dot.gz`：隔离离线审计。使用已有研究 clone，未替换正式源码；Docker 禁用网络，BitBake 设置 `BB_NO_NETWORK=1`。解析 2939 个配方、0 错误，构建图包含 286 个配方及 4883 个任务节点，无依赖环。原始任务图仅作 gzip 压缩。
- `network-required-domains.json`：从当前配方确认的源码和构建支持站点，已保存到云环境配置草稿。列表不保证涵盖所有后续重定向；保存草稿不等于运行时已应用。

任务图确认 guest 包安装依赖 `pi4-guest1-image:do_image_complete` 和 `linux-yocto:do_deploy`，整卡 Wic 任务依赖 Xen、U-Boot 及启动脚本部署。新增构建来源记录也在这次离线解析范围内。

研究 layer 提交与候选锁定值相同，但本次尚不能通过官方源确认，因此离线解析成功不能写成正式源构建成功。还需联网核实 Pi4 的 `KBRANCH` 与 `SRCREV_machine`；当前元数据保留了通用 Poky 默认提交，未猜测或替换为未经验证的 Pi4 分支提交。

后续只有实际完成官方源码获取、BitBake 编译、整卡检查及 `scripts/qemu-yocto.sh validate` 后，才能增加对应 PASS 证据。历史 Debian QEMU 记录不属于本次验收。
