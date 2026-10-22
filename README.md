# BakaSU：android12-5.10 / 最新 SUSFS 适配测试分支

这是 `suhuli/BakaSU` 的 **`susfs-android12-5.10` 下游测试分支**，基于最新上游 main `dac2d186`，面向一加 Ace 竞速版（MT6895 / Android 13 / Linux 5.10.110）。不是上游正式版，也不代表已通过实机验证。

- 对接 `gki-android12-5.10` 最新 SUSFS（适配基线 `f43926dc`，v2.3.0）。
- 修复 SELinux 三个外部接口，并保留 5.10 所需的 `fake_state`。
- **保留 BakaSU 现有 init.rc / ksud 启动链，显式关闭尚未移植的新 preinit runner；没有添加空函数。**
- 配合 [Action-Build-Plus](https://github.com/suhuli/Action-Build-Plus) 的 `test/bakasu-latest-susfs` 分支使用；选择 `BAKASU`，旧版回退选项 `RESUKISU` 保留。
- 管理器使用未改动的最新上游源码基线所对应的官方签名 APK；内核版本号与之绑定，实际修补提交仍显示在内核名称中。

完整设计、来源、限制、验证方式见 [适配说明](docs/susfs-android12-5.10.md)。刷入前必须备份已确认能用的 `boot`。

```sh
python3 -m unittest discover -s tests -v
```

许可证及上游项目说明保持原样。SELinux 兼容改动参考官方 `sync-susfs` 工作及 xmicro 的修复，详见适配说明。
