# Stadia Controller 逆向资料归档

Google Stadia Controller（型号 H2B / G020F）的离线资料库：固件、FCC 文件、社区仓库快照、协议文档与中文汇编。

- **归档日期**：2026-11-25
- **文件总数**：80（不含本文件与 `NOTICE.md`）
- **总体积**：约 224 MB
- **校验清单**：[`MANIFEST.csv`](MANIFEST.csv)（每个文件的 SHA-256 与字节数）

## 目录结构

| 目录 | 内容 | 体积 |
|---|---|---|
| `docs/` | 中文汇编《Stadia 手柄逆向工程资料汇编》的 Markdown 与 Word 版 | 0.1 MB |
| `firmware/` | 官方固件镜像：11 个 gotham（Wi-Fi）OTA、3 个 bruce（蓝牙）镜像、flashloader 与 FCB、vouiren 提供的 SHA-512 | 46 MB |
| `hardware/` | FCC 备案 A4R-H2B 的 17 份公开 PDF（内部/外部照片、SAR、测试报告、用户手册等） | 32 MB |
| `repos/` | 22 个社区仓库的 zipball 快照（含固件备份、刷机工具、协议实现、内核补丁说明等） | 146 MB |
| `tools/` | 抓取脚本、固件提取脚本、Markdown→Word 生成脚本 | < 1 MB |

## 固件清单

`firmware/gotham-ota/`（原厂 Wi-Fi 固件，A/B 槽与 dvt/pvt 通道都在）：

| 构建号 | 通道 | 槽位 |
|---|---|---|
| 169429 | stable | pvt-b |
| 235551 | stable | pvt-a |
| 259108 | stable | pvt-b |
| 269117 | stable | pvt-a / pvt-b |
| 282115 | stable | pvt-a / pvt-b |
| 316382 | beta | dvt-a / dvt-b |
| 316382 | stable | pvt-a / pvt-b |

`firmware/bruce/`：`bruce_pvt_a_prod_signed.bin`、`bruce_dvt_a_stage_signed.bin`、`bruce_dvt_a_dev_signed.bin`（均来自官方刷机页）。

`firmware/flashloader/`：`restricted_ivt_flashloader.bin`、`flashloader_fcb_get_vendor_id.bin`、`flashloader_fcb_w25q128jw.bin`。

## 关键校验

`ota.282115.stable-channel.gotham-pvt-a.*.bin` 的 SHA-256 为：

```
269bb21160ea6d1366e71bb9c9b148e2782ea967b81c7b6ff038e7d49b61e00f
```

与社区公开参考值一致；同一文件也已从 Google OTA CDN 现场下载比对，字节完全相同。

## 来源

- 固件：Google OTA CDN（`edgedl.me.gvt1.com`）与各社区仓库（vouiren/StadiaFW、StadiaMemories/firmware、Scyne/stadiaRawBtFw 等）。
- FCC 文件：`https://fccid.io/A4R-H2B`（原始出处为 FCC 公开数据库）。
- 仓库：`codeload.github.com` 的 zipball，抓取时点即归档日期。
- 文档：本次整理产出，来源见正文引用。

## 未能收录

- **NXP i.MX RT1060 参考手册（IMXRT1060RM.pdf）**：NXP 站点对脚本请求返回 404，未抓取。请从 NXP 官网手动下载（约 55 MB）。
- **FCC 原理图 / 框图 / Theory of Operation**：FCC 页面上标注为 "Metadata only"，本身不提供 PDF。
- **各平台可执行文件、拆机视频**：不属于资料本体，未收录。

## 使用建议

1. 先读 `docs/` 里的汇编，第 4、6、7、8 节是刷机与协议的核心。
2. 需要刷机时用 `firmware/bruce/` + `repos/ChristopherKlay__stadiacontroller.zip`（或 `repos/luigimannoni__stadia-controller-flasher.zip`）。
3. 需要回退 Wi-Fi 固件时用 `firmware/gotham-ota/` 对应槽位的镜像。
4. `repos/*.zip` 解压后保留原始目录结构，内含各项目自己的 LICENSE。

## 版权

见 [`NOTICE.md`](NOTICE.md)。**本仓库为私人存档，请勿公开再分发固件。**
