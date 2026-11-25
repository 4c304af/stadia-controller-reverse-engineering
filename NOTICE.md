# 版权与使用声明

本仓库是个人研究用的离线归档，不是任何项目的官方分发渠道。

## 固件

`firmware/` 下的所有 `.bin`（gotham OTA、bruce 镜像、flashloader、FCB）版权归 **Google LLC** 所有。它们原本由 Google 通过 `stadia.google.com/controller` 与 OTA CDN 公开发布，用于让用户把已购买的手柄更新为蓝牙模式。

本仓库保存这些文件的目的仅是：在官方渠道下线后，仍能对自己拥有的硬件做互操作研究与恢复。**请勿公开再分发、商用或用于任何规避版权保护的用途。** 若版权方提出要求，应立即删除。

## FCC 文件

`hardware/fcc/` 下的 PDF 来自美国联邦通信委员会（FCC）公开数据库，属美国政府公开记录。

## 社区仓库

`repos/` 下是各 GitHub 仓库的 zipball 快照，版权归各自作者所有，许可证见压缩包内的 `LICENSE` 文件。较重要的几个：

| 仓库 | 许可证 |
|---|---|
| GaryOderNichts/StadiaController | MIT |
| jkfran/stadiacast | MIT |
| 其余 | 见各自 LICENSE |

## 商标

Stadia、Google 及相关标识是 Google LLC 的商标。本仓库与 Google 无关联。

## 风险

固件刷写可能导致设备变砖；BootROM 相关研究涉及安全边界。使用本仓库内容造成的任何后果由使用者自行承担。
