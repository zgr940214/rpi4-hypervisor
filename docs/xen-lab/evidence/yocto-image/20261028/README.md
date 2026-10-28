# 自建 Yocto 整卡的实际交付证据

本目录顶层记录最终镜像；`initial/` 保留此前成功构建但首次 QEMU guest 创建失败的原始记录。没有用历史 Debian 镜像代替本次验证。

- 构建：`build-export.log`，正常 `./scripts/container.sh build` 完成 BitBake、导出与静态检查，进程退出 0。
- 静态检查：`image-checks.json`，41 项 PASS。3 项 NOT_RUN 分别为静态检查不能完成的 SSH 登录、Pi4 硬件启动、固件/U-Boot/EL2 行为。
- 实际 QEMU：`report.json`、`serial.log`、`ssh-guest-console.log` 和 `qemu-validation.log`。2026-10-28 13:16:22–13:18:20 UTC，10/10 项通过，31/31 条目标命令退出 0；包括实际 SSH 登录。验证命令 `./scripts/qemu-yocto.sh validate` 退出 0。
- 同一产物：`provenance.json` 绑定整卡、从卡内提取的 Xen/Linux，以及构建和静态检查证据；guest 使用 Dom0 中的原有磁盘。QEMU 使用 `-snapshot`，验证后源整卡 SHA256 未变。
- 源码清单：`source-manifest.json`、`source-manifest.log`、`pn-buildlist` 和 `task-depends.dot`，记录实际选择的 224 项源码与 232 个配方。
- 工具测试：`tool-tests.log`，99 项通过、无跳过。
- 镜像交付：`repository-image-pack.log`、`repository-image-restore.log` 和 `repository-restore.json`。两份分片合计 63,271,860 字节；真实还原到独立文件后，再次计算原镜像及还原文件的完整摘要，大小与 SHA256 均一致。

最终镜像为 1,295,329,280 字节，SHA256：

```text
49fe88a3649b446cabcda7aa7c27ad81845bb950a3cfe602b0d057d5ab53e305
```

首次 QEMU 的确启动了 Xen 和 Dom0，但 Xen 4.19 把磁盘参数中 `target=` 后面的内容都解析为路径，导致 guest 创建失败。修复将 `target=` 放在最后，增加回归检查，再由 Yocto 正规重建整卡。其后进行了本目录记录的完整成功验证。旧报告未改写为成功。

QEMU 机型为 ARM `virt`，直接加载这张卡内的 Xen 与 Linux。Pi 固件、U-Boot、Pi4 设备树及物理 SD/网卡启动尚无板卡实测。TEE、安全启动和加密服务未在本阶段实现。
