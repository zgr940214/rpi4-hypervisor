# QEMU 证据说明

**完整验证 PASS：10 项检查通过，31 条目标命令退出码均为 0。** 实际运行时间为 2026-10-28 16:45:24–16:47:25（北京时间；原始报告使用 UTC）。

本目录保留真实 ARM64 QEMU 运行和构建记录。最终结果见 `report.json`，命令总退出码见 `validation.log`；原始 PTY 输出保留回车和 ANSI 控制字符。

- `serial.log`：Xen、Dom0、guest1 首次启动和再次创建的实际控制台。
- `ssh-guest-console.log`：SSH 公钥认证到 Dom0，连接 guest 控制台、计数和恢复后的 shell。
- `xen.dts`、`xen.json`：实际使用的设备树与加载地址。
- `kernel.config`、`xen.config`、`rootfs-packages.tsv`、`xen-source-commit.txt`：实际构建版本和配置。
- `source-sha256.json`：本次运行使用的构建、控制器和目标脚本摘要。
- `helper-tests.log`：49 项工具测试通过；独立于 QEMU 集成测试。
- `container-build.log`、`xen-build.log`、`rootfs-build.log`、`rootfs-export.log`：构建和文件系统检查原始输出。

`report.json` 中的 `/work/` 是构建容器内的仓库路径。Dom0 和 guest 使用独立 Debian ARM64 验证文件系统；本目录不表示 Pi4 Yocto 镜像或实机启动通过。QEMU 结束由控制器主动终止进程，报告会记录信号状态；测试总退出码以 `validation.log` 为准。

## 修复过程中的失败与中断

`earlier-attempts/` 保留此前各轮原始报告，均未作为完整通过结果：

| UTC 运行目录 | 结果与原因 |
| --- | --- |
| `20261028T075758Z` | 串口长输入与回车处理导致控制器等待，手动中断。 |
| `20261028T080241Z` | root shell 已到达，但 ANSI 控制序列使 UID 输出断言失败。 |
| `20261028T080517Z` | guest 已启动并写文件；Ctrl+] 与回车合并导致控制台未退出，手动中断。 |
| `20261028T083550Z` | SSH、暂停恢复已通过；关机通知早于域销毁完成，旧断言退出登录，手动中断。附 Dom0 域监控日志。 |
| `20261028T084001Z` | Xen 合法的 `-bp---`（blocked 与 paused 同时置位）被旧状态断言误判。 |
| `20261028T084318Z` | 已通过正常关机并开始重建；为合并控制台缓冲与提示符等待修复而中断。 |

控制器现检查独立状态位、等待域清理、消费已有控制台缓冲，并在中断计数后等待 shell 提示符。暂停状态、计数停止/继续、UUID、磁盘持久化等功能断言均保留。
