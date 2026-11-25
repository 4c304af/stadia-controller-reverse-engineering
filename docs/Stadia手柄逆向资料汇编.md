# Google Stadia 手柄逆向工程资料汇编

**整理时间**：2026-11-25　**对象**：Google Stadia Controller（型号 H2B / G020F，2019–2023）

**这份文档解决什么问题**：Stadia 云服务已于 2023-01-18 关停，官方刷机页 `stadia.google.com/controller` 也在 2026 年初彻底下线。但这个手柄是一块做工扎实、资料已被社区挖得相当透的硬件：主控是 NXP i.MX RT1061，无线是 Broadcom BCM43458F，16 MB SPI NOR，带霍尔扳机、双马达、麦克风和耳麦口。下面把散落在博客、GitHub、FCC、论坛里的资料按"能用来干什么"重新组织，并标注每一项在 2026-11 是否还活着。

---

## 0. 先读这六篇

如果只看六份材料，按这个顺序：

| 序号 | 材料 | 为什么必读 |
|---|---|---|
| 1 | [GaryOderNichts：Looking into the Stadia Controller Bluetooth Mode Website](https://garyodernichts.blogspot.com/2023/01/looking-into-stadia-controller.html) | 目前唯一把官方刷机流程（OEM → Bootloader → SDP → Flashloader）完整拆开讲清楚的文章，附 Python 工具 |
| 2 | [Chrome 团队：Talking to the Stadia controller with WebHID](https://developer.chrome.com/blog/talking-to-the-stadia-controller-with-webhid) | 官方视角的 USB HID 层说明，给出 VID/PID、report ID、10 字节输入报告的字段含义 |
| 3 | [lidskialf：Taking a Google Stadia Controller Apart and Dumping its ROM](https://blog.lidskialf.net/2021/04/07/taking-a-google-stadia-controller-apart-and-dumping-its-rom/) | 第一手的拆机 + 芯片型号 + 1.8V NOR 读取 + FlexSPI 启动头解析 |
| 4 | [stadiacast：docs/protocol.md](https://github.com/jkfran/stadiacast/blob/main/docs/protocol.md) | 把 Wi-Fi 模式的整套网络协议（HTTPS 引导、RPC、GMsg、WebRTC/DTLS、输入、音频、BLE 配网）从固件里还原了出来 |
| 5 | [tchebb：nxp-sdp-overrun](https://codeberg.org/tchebb/nxp-sdp-overrun) | i.MX RT1060 BootROM 的 3 字节溢出，一条 USB 传输拿到代码执行，等于给"HAB 闭合"开了个洞 |
| 6 | [DJm00n/ControllersInfo：stadiacontroller](https://github.com/DJm00n/ControllersInfo/tree/master/stadiacontroller) | USB/BLE 的 HID 描述符原文 + pcap 抓包，做协议分析时的基准数据 |

三条典型路线，按需取用：

- **只想让手柄能用**：第 6 节的刷机工具 + 第 10 节的驱动/适配器，半小时能搞定。
- **想弄清协议、写自己的工具**：第 4、7、8 节，配 Gary 的 stadiatool 和 stadiacast。
- **想做固件/硬件级逆向**：第 3、5、9 节，涉及拆 flash、Ghidra、BootROM 漏洞。

---

## 1. 硬件与型号基线

先把"这东西到底是什么"钉死，后面所有资料才有坐标系。

| 项目 | 参数 | 依据 |
|---|---|---|
| 型号 | H2B（FCC ID `A4R-H2B`），零售型号 G020F | [FCC 备案](https://fccid.io/A4R-H2B)、[LegendaryTech 规格页](https://www.legendarytech.io/google/stadia/stadia-controller) |
| 主控 | NXP **i.MX RT1061**（Arm Cortex-M7 crossover MCU，片内 512 KB SRAM） | lidskialf 拆机、gomezluisj 硬件文档 |
| 无线 | **Broadcom BCM43458F**（Wi-Fi + Bluetooth combo） | gomezluisj、LegendaryTech |
| 存储 | **16 MiB（128 Mbit）1.8V SPI NOR**；实测有 Zetta 25LQ128、Winbond W25Q128JW 等批次 | lidskialf、GaryOderNichts |
| 电池 | 2000 mAh 锂电，USB-C 充电，不可用户更换 | [9to5Google 拆解报道](https://9to5google.com/2019/11/27/stadia-controller-teardown/) |
| 扳机 | **霍尔效应传感器 + 磁铁**（非电位器），L2/R2 由 GPIO2_10 使能 | lidskialf、gomezluisj |
| 振动 | 左右马达配重不同（左侧约为右侧 3 倍） | lidskialf |
| 按键 | 19 个；标准 HID 描述符只暴露 17 个，Assistant / Capture 需走额外通道 | Chrome WebHID 博客 |
| 接口 | USB-C（供电 / 有线 / Tandem 串联）、3.5 mm 耳麦、麦克风、状态灯 | [Google 支持页](https://support.google.com/stadia/answer/13067284) |
| 无线模式 | 原为 Wi-Fi 直连 Google 边缘节点（降延迟）；刷蓝牙固件后改为 **BLE**（HID over GATT） | Google 支持页、DJm00n |

一个容易被忽略的事实：**它原本不是蓝牙手柄**。出厂固件（代号 gotham）只有 Wi-Fi 直连 + USB 有线；蓝牙能力是 2023 年 Google 在关服时通过一次"固件更新"解锁的（代号 bruce）。所以"逆向 Stadia 手柄"实际上分两条完全不同的技术栈：**Wi-Fi 模式**（原版固件、私有网络协议）和**蓝牙模式**（新固件、标准 BLE HID）。两条线下面分开讲。

---

## 2. 官方与准官方资料

| 资料 | 链接 | 价值 | 2026-11 状态 |
|---|---|---|---|
| Stadia Controller 蓝牙模式页 | `https://stadia.google.com/controller/` | 官方 WebUSB/WebHID 刷机入口，本身就是一个可分析的 Web 应用 | **已下线**，只剩占位页 |
| Wayback 存档 | [web.archive.org 快照](https://web.archive.org/web/20230131181508/https://stadia.google.com/controller/) | 页面文案、配对说明（Y+Stadia 2 秒）、支持设备列表 | 可用 |
| 支持文档：连接手柄 | [support.google.com/stadia/answer/13067284](https://support.google.com/stadia/answer/13067284) | 官方刷机步骤、充电 ≥10% 要求、Linux 需要 udev 规则 | 可用（文案有过期） |
| Chrome WebHID 博客 | [developer.chrome.com](https://developer.chrome.com/blog/talking-to-the-stadia-controller-with-webhid) | VID `0x18d1` / PID `0x9400`、report ID 3、10 字节报告逐字节解释 | 可用 |
| FCC 备案 A4R-H2B | [fccid.io/A4R-H2B](https://fccid.io/A4R-H2B) | **内部高清照片**、框图、原理图（部分仅元数据）、天线与芯片布局 | 可用 |
| iFixit 拆解指南 | [ifixit.com Guide 143461](https://www.ifixit.com/Guide/Google+Stadia+Controller+Opening+Procedure/143461) | 卡扣位置、隐藏螺丝、排线风险 | 可用 |
| Gamers Nexus 拆解视频 | 见 9to5Google 报道内嵌 | 首次公开拆解，展示"无可见螺丝"的结构设计 | 视频仍在 |
| TechInsights BOM | [techinsights.com/products/bom-1911-812](https://www.techinsights.com/products/bom-1911-812) | 付费器件清单，芯片型号最权威 | 付费 |
| Steam 支持变更 | [9to5Google 2025-12-11](https://9to5google.com/2025/12/11/steam-google-stadia-controller-support/) | 2025 年底 Steam 原生识别手柄，Stadia 键映射为 Xbox 键 | 可用 |

> 说明：官方刷机页虽然下线，但页面本体（HTML+JS+固件 bin）被多份 GitHub 仓库完整备份，见第 6 节。这是目前**唯一还能给未刷机手柄解锁蓝牙**的途径。

---

## 3. 拆解、芯片识别与固件读取（硬件层）

### 3.1 lidskialf 的拆机与 ROM dump（最详细的一手记录）

原文：[blog.lidskialf.net](https://blog.lidskialf.net/2021/04/07/taking-a-google-stadia-controller-apart-and-dumping-its-rom/)

关键结论：

- **拆法**：背面有一块塑料盲板，加热软化胶后撬开，露出唯一一颗螺丝；其余全靠大量卡扣，容易崩边。作者标了卡扣位置图。
- **芯片**：主控 NXP i.MX RT1061；flash 为 Zetta `25LQ128`（128 Mb = 16 MiB），**1.8V** 器件。
- **读取**：先用 Raspberry Pi Pico 失败（3.3V 电平转换太慢），换 **PICkit 2**（可 1.8V 直连）+ `flashrom -p pickit2_spi -r dump.bin` 成功。
- **启动头**：偏移 `0x0` 是 `FCFB`（FlexSPI NOR Configuration Block），`0x1000` 是启动头，指向 `0x60801000`，减去 `0x60000000` 映射基址即 `0x801000`；代码段是 ARM Thumb。
- **字符串**：固件里能看到 Google 内部路径 `.../gotham/source/yeti/yeti_http_client.cc`、`cloudcast-pa.googleapis.com` 等 —— 直接印证了 Wi-Fi 直连的业务链路。
- **调试口**：板上有一处未焊接的调试排针（作者用万用表"蜂鸣档"逆向了一部分定义，未完成）。2025 年有读者反馈存在**已焊接调试口 + 外壳开孔**的工程样机版本。

### 3.2 FCC 内部照片

`A4R-H2B` 的 Internal Photos（3.9 MB PDF）是免费且高清的板级照片来源，能看到 BCM43458F、屏蔽罩、天线走线、马达与电池布局。做硬件逆向时优先看这个，而不是网上的二手拆机图。

### 3.3 gomezluisj 的硬件/引脚参考

仓库：[gomezluisj/stadia-controller-re](https://github.com/gomezluisj/stadia-controller-re)

自称在 PVT 实机上验证过，内容包括：

- 摇杆/扳机接 `ADC1`；L2/R2 霍尔使能 `GPIO2_10 = 0`（低有效）
- 17 个按键的 GPIO 映射
- BCM43458F 走 `LPUART3` + CTS strap，固件里带 `.hcd`（patchram）蓝牙补丁
- I2C 器件：`BQ25601`（充电）、`WM8904`（音频 codec）、`TS3A227E`（耳麦检测）、`BQ2742X`（电量计）、`LP5562`（LED 驱动）
- NOR 分区、`KVS` 键值存储格式、`BEE Region 1`（AES-128-ECB）几何结构

这个仓库星不多，但信息密度很高；建议与 lidskialf、FCC 照片交叉验证后使用。

### 3.4 硬件层的坑

- flash 是 **1.8V**，直接上 3.3V 编程器（CH341A 默认 5V/3.3V）会烧片，必须加 1.8V 电平转换或专用适配器。
- 卡扣极紧，iFixit 与 Gamers Nexus 都强调"先加热、从手柄下缘起撬"。
- 电池粘在底壳上，拆解时容易被刺穿。

---

## 4. 固件体系：gotham / bruce 与刷写链路

这一节是整份资料的技术核心，几乎全部来自 [GaryOderNichts 的逆向](https://garyodernichts.blogspot.com/2023/01/looking-into-stadia-controller.html)。

### 4.1 两套固件代号

| 代号 | 含义 | 版本号 | 备注 |
|---|---|---|---|
| **gotham** | 原厂 Wi-Fi 固件 | `< 0x4E3E0`（320480） | 关服后官方不再提供下载，只能靠社区 dump |
| **bruce** | 蓝牙模式固件 | `>= 0x4E3E0` | 官方刷机页实际刷入的镜像 |

版本号与槽位（据社区 dump 整理）：

| build | 代号 | 槽位 | 说明 |
|---|---|---|---|
| 235551 | gotham | — | 早期 Wi-Fi 固件；据 gomezluisj 的哈希比对，流传的 `gotham235551.elf` 实为 OTA 282115 的 ELF 封装 |
| 282115 | gotham | Slot A（`0x60040000`） | **官方 OTA 直链目前仍可下载**，见 5.1 |
| 316382 | gotham | Slot B（`0x60840000`） | 后期 Wi-Fi 固件 |
| 337784 | bruce | Slot A | 蓝牙固件，即刷机页刷入的版本 |

命名规则：`<代号>_<dvt|pvt>_<a|b>_<dev|stage|prod>_signed.bin`。`dvt` = 开发样机、`pvt` = 量产；`dev/stage/prod` = 开发/预发布/正式签名。**刷错组合会变砖**，官方页会先读 USB 序列号前缀来判定 dvt/pvt。

### 4.2 四种 USB 模式与进入方式

| 模式 | 触发方式 | VID:PID | 设备名 | 能力 |
|---|---|---|---|---|
| 应用（OEM） | 正常插线 | `18d1:9400` | Stadia Controller | HID 手柄 + 厂商专用 bulk 接口，可读固件版本/电量 |
| Bootloader | **按住 Option（三点）键**再插线 | `18d1:946b`（社区整理） | — | 等待组合键进入 SDP |
| SDP | Bootloader 下按 **Option + Assistant + A + Y** | `1fc9:0135` | SP Blank RT Family | NXP 串行下载协议，可写内存、跳转执行 |
| Flashloader | 由 SDP 载入并跳转 | `15a2:0073` | USB COMPOSITE DEVICE | 受限 flashloader，可擦写 NOR |

官方页在 OEM 模式下通过 USB 控制请求读取信息：`0x81` 取固件版本、`0x83/0x84` 取电量（低于 10% 拒绝刷机）。

### 4.3 刷写流程（照 Gary 的拆解复述）

1. **SDP 上传**：用 `WRITE_FILE` 把 `restricted_ivt_flashloader.bin` 写到 `0x20000000`，再 `JUMP_ADDRESS` 跳到 `0x20000400`。
2. **识别 MCU**：读 `0x400D8260`，只接受 `106XA0` / `106XA1` 两种。
3. **识别 flash**：先加载 `flashloader_fcb_get_vendor_id.bin`（FCB 里把读数据的 LUT 序列换成"读厂商/设备 ID"），再用 `WriteMemory/ReadMemory` 直接操作 FlexSPI 寄存器，从 RX FIFO 取回 ID。
4. **配置 flash**：Winbond 片加载 `flashloader_fcb_w25q128jw.bin`；GigaDevice 片由 flashloader 按配置值 `0xC0000206` 自动配置。
5. **写固件**：清 GPR4–6，解析镜像 build info，`FlashEraseRegion` 擦除，`WriteMemory` 写入 `0x60040000` 映射区，IVT 写到 `0x60001000`。
6. **收尾**：GPR6 设为启动槽，`Reset` 重启。

### 4.4 内存映射（做固件分析必备）

| 区域 | 地址 | 说明 |
|---|---|---|
| FlexSPI NOR 窗口 | `0x60000000` | 16 MiB flash 的线性映射 |
| FCB | `0x60000000` | 首 4 字节 `FCFB` |
| IVT | `0x60001000` | 镜像向量表 |
| Slot A 应用 | `0x60040000` | gotham 282115 / bruce 337784 |
| Bootloader | `0x60800000` | 128 KB，独立签名 |
| Slot B 应用 | `0x60840000` | gotham 316382 |
| OCRAM | `0x20200000` | flashloader、自定义 RAM 代码 |
| DTCM | `0x20000000` | 512 KB 紧耦合内存 |
| FlexSPI 外设 | `0x402A8000` | 寄存器级读 flash 的入口 |
| SRC GPR | `0x400F8000` 起 | GPR6 = 启动槽选择（Gary 已证实）；GPR7 的更新位含义仍属研究推断 |

> Gary 的取巧点：受限 flashloader 不允许直接 `ReadMemory` 读 flash，但允许读写 FlexSPI 寄存器。于是他加载正常 FCB、发 `Read Data` 序列、从 RX FIFO 一次取 4 字节，**几小时**把整片 flash dump 了出来。这是"用外设寄存器绕过命令白名单"的经典案例。

### 4.5 官方刷机页到底加载了哪些文件

| 文件 | 作用 |
|---|---|
| `restricted_ivt_flashloader.bin` | 受限 flashloader，经 SDP 载入 OCRAM |
| `flashloader_fcb_get_vendor_id.bin` | 读 flash ID 用的 FlexSPI 配置块 |
| `flashloader_fcb_w25q128jw.bin` | Winbond 128 Mb 的完整 FCB |
| `bruce_pvt_a_prod_signed.bin` | 蓝牙固件（量产版） |
| `bruce_dvt_a_dev_signed.bin` / `bruce_dvt_a_stage_signed.bin` | 开发/预发布签名镜像 |
| `gotham_*_signed.bin` | Wi-Fi 固件，官方站已 404，只能靠 dump |

原始 URL 形如 `https://stadia.google.com/controller/data/<文件名>`，现在全部跳到占位页；文件本体在各 GitHub 存档里（第 5 节）。

---

## 5. 固件镜像与抓取

### 5.1 仍在线的官方 OTA（重要）

Google 的 OTA CDN 至今仍返回 gotham 282115 的完整镜像（4,163,944 字节，与社区记录的大小/哈希一致）：

```
https://edgedl.me.gvt1.com/edgedl/googletv-eureka/stable-channel/ota.282115.stable-channel.gotham-pvt-a.214f6fe20f7b993046c77a9245c5805b056882dc.bin
```

文件开头就是 Cortex-M 向量表（`0x2003F688` 初始栈指针，复位向量指向 `0x6004xxxx`），确认是 Slot A 应用镜像本体。这条链接来自 2022 年 Reddit 用户贴出的官方更新地址，**2026-11-25 实测仍 200**。它是目前唯一无需拆机、无需刷机就能拿到的原厂 Wi-Fi 固件。

### 5.2 GitHub 上的固件存档

| 仓库 | 内容 | 备注 |
|---|---|---|
| [Scyne/stadiaRawBtFw](https://github.com/Scyne/stadiaRawBtFw) | 官方刷机页拉取的原始 bin + 解锁步骤图解 | 最常被引用的备份，含 `bruce_pvt_a_prod_signed.bin` |
| [merlinschumacher/Stadia-Controller-Bluetooth-Firmware-Bin](https://github.com/merlinschumacher/Stadia-Controller-Bluetooth-Firmware-Bin) | 同上，附刷写顺序与 Reddit 教程链接 | 文件较小，适合快速取用 |
| [StadiaMemories/firmware](https://github.com/StadiaMemories/firmware) | 固件 + 刷机页用到的其它文件 | 组织名即"保存 Stadia 遗产" |
| [vouiren/StadiaFW](https://github.com/vouiren/StadiaFW) | **蓝牙 + Wi-Fi 双固件 dump** | 想回退 gotham 时找它 |
| [ricky8k/Stadia-Controller-Firmware](https://github.com/ricky8k/Stadia-Controller-Firmware) | 官方固件归档 + 解锁 Bootloader 图文 | README 步骤写得很清楚 |
| [luigimannoni/stadia-controller-flasher](https://github.com/luigimannoni/stadia-controller-flasher) | 官方页面的本地备份 + 可刷 gotham 的改造版 | 见 6.1 |

> 版权提醒：这些 bin 是 Google 的版权作品，仓库能存在是因为"保存已停服设备的可用性"这一共识。自己留存、研究可以，不要再分发或商用。

### 5.3 自己 dump 的三条路

1. **走 flashloader（不改焊）**：用 Gary 的 `stadiatool dump <start> <end> <out>`，4 字节一次，慢但安全，需要先进入 Flashloader。
2. **拆 flash 直读**：lidskialf 的路线，PICkit 2 / 1.8V 适配的 CH341A + `flashrom`，最快最完整。
3. **寄存器级脚本**：gomezluisj 的 `nor_slice_inspect.py` / `ivt_csf_inspect.py` 可在 dump 之后做分区切割与签名范围审计。

---

## 6. 刷机与回退工具现状（2026-11 实测）

| 工具 | 地址 | 作用 | 状态 |
|---|---|---|---|
| Christopher Klay 的官方页镜像 | [christopherklay.github.io/stadiacontroller](https://christopherklay.github.io/stadiacontroller/) | 与官方页几乎一致的 WebUSB 刷机流程 | **可用**，目前最推荐 |
| 仓库备份 | [ChristopherKlay/stadiacontroller](https://github.com/ChristopherKlay/stadiacontroller) | 未改动的官方页面备份 | 可本地起服务 |
| luigimannoni 非官方刷机器 | [luigimannoni.github.io/stadia-controller-flasher](https://luigimannoni.github.io/stadia-controller-flasher/) | 可刷 bruce，也可刷回 gotham；URL 参数 `device_type` 切换 pvt/dvt/dev | **可用** |
| hazrpg 本地副本 | [hazrpg/stadia-flasher](https://github.com/hazrpg/stadia-flasher) | 官方页的离线拷贝 | 需 `--allow-file-access-from-files` 启动 Chrome |
| GaryOderNichts/stadiatool | [GaryOderNichts/StadiaController](https://github.com/GaryOderNichts/StadiaController) | 命令行：`info` / `flashloader` / `flash_firmware` / `dump` / `reset` | 可用，Linux 为主 |
| fcb_parser | 同上子目录 | 解析 `flashloader_fcb_*.bin`，理解 FlexSPI 配置 | 可用 |

**刷机注意**：

- 全程用 **Chrome/Edge 108+**，必须有 WebUSB 权限；Linux 需要先装 udev 规则。
- 电量 ≥ 10%，用能传数据的 USB-C 线（很多充电线没有 D+/D-）。
- 一旦刷成 bruce（蓝牙），官方口径是**不可逆**；回退 gotham 要用社区工具 + 对应镜像，且并非所有批次都验证过。
- 刷错 `dvt/pvt` 或 `dev/stage/prod` 组合会直接变砖，恢复需要 SDP + flashloader。

Linux udev 规则（来自 Google 官方规则，社区整理在 [NixOS 论坛帖](https://discourse.nixos.org/t/google-stadia-controller-udev-rules-for-flashing-bluetooth-firmware/64439)）：

```
# SDP 协议
KERNEL=="hidraw*", ATTRS{idVendor}=="1fc9", MODE="0666"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="1fc9", MODE="0666"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0d28", MODE="0666"
# Flashloader
KERNEL=="hidraw*", ATTRS{idVendor}=="15a2", MODE="0666"
# 手柄本体
KERNEL=="hidraw*", SUBSYSTEM=="hidraw", ATTRS{idVendor}=="18d1", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="18d1", ATTRS{idProduct}=="9400", MODE="0660", TAG+="uaccess"
```

---

## 7. USB / HID 协议细节

### 7.1 USB 描述符（有线模式，DJm00n 抓取）

设备级：`bcdUSB 0x0201`、`bDeviceClass 0xEF`（Miscellaneous）、`VID 0x18d1`、`PID 0x9400`、`bcdDevice 0x0100`、字符串 `"Google Inc."` / `"Stadia Controller"` / 序列号。

配置：2 个接口，总线供电，`bMaxPower 500 mA`。

| 接口 | 类型 | 端点 | 说明 |
|---|---|---|---|
| IF0 | Vendor Specific（IAD 0xFF） | `0x87` IN / `0x07` OUT，Bulk，512 B | 厂商 RPC：固件版本、电量、刷机控制 |
| IF1 | HID（IAD 0x03） | `0x83` IN / `0x03` OUT，Interrupt，64 B，bInterval 6 | 标准手柄输入 + 输出报告（震动） |

HID 描述符：`bcdHID 0x0111`，report descriptor 长度 `0x9C`（156 字节）。

### 7.2 报告格式

- **输入报告 ID 3**，10 字节。Chrome 博客给出的解码：`data[0] == 8` 表示"功能键组"，`data[1]` 的位含义为 `1 = Capture`、`2 = Assistant`、`3 = 同时按下`。
- **输出报告 ID 5**：震动。内核驱动按两个 16 位字段解析（strong / weak magnitude），见 7.5。
- 其余按键/摇杆走标准 Gamepad 映射（17 键 + 4 轴），所以不经过 WebHID 也能用。

### 7.3 BLE HID 描述符（蓝牙模式）

DJm00n 抓到的 BLE report descriptor 共 182 字节，结构：

- Report ID 3：4 位 Hat switch + 4 位 padding；15 个 Button 位（usage 1,2,4,5,7,8,11–15,17–20）；X/Y（8 位）、Z/Rz（8 位）
- Report ID 5：震动输出（与 USB 一致）

它本质上是"标准手柄 + 两个额外按键"，这也是为什么 Switch/Android/Steam 能直接识别，但 Assistant/Capture 默认无功能。

### 7.4 SDL 映射（跨平台兼容性的参照）

[SDL_GameControllerDB](https://github.com/mdqinc/SDL_GameControllerDB) 里已有官方条目，GUID 直接暴露了总线类型：

```
03000000d11800000094000000000000,Google Stadia Controller,...,platform:Windows
05000000d11800000094000001000000,Google Stadia Controller,...,platform:Linux
```

`03` 开头 = USB，`05` 开头 = Bluetooth；中间 `d118 0000 0094 0000` 即 VID/PID 的小端表示。写自己的驱动/映射时可以直接抄这份映射表。

### 7.5 Linux 内核驱动

上游已有 `drivers/hid/hid-google-stadiaff.c`（2023-08-14 合入，**Linux 6.6 起**），配置项 `CONFIG_HID_GOOGLE_STADIA_FF`：

- 匹配 `HID_USB_DEVICE` 与 `HID_BLUETOOTH_DEVICE` 两种 `18d1:9400`
- 只负责**震动**：`STADIA_FF_REPORT_ID 5`，两个 16 位幅值，`input_ff_create_memless`
- 输入部分交给 `hid-generic` + SDL/Steam

源码：[torvalds/linux · hid-google-stadiaff.c](https://github.com/torvalds/linux/blob/master/drivers/hid/hid-google-stadiaff.c)

---

## 8. Wi-Fi 模式协议（原版 gotham 固件）

这是 Stadia 手柄最独特、也最少人碰的部分：它不经过主机，**自己连 Wi-Fi 直连 Google 边缘节点**。关服后这条链路本该彻底死亡，但 [stadiacast](https://github.com/jkfran/stadiacast) 用本地服务器把它完整复刻了回来，并把协议写成了 [docs/protocol.md](https://github.com/jkfran/stadiacast/blob/main/docs/protocol.md)。

### 8.1 启动序列（HTTPS）

固件只会 HTTP/1.1，protobuf body 用 `application/x-protobuf`，任何非 200 都视为 RPC 失败。依次请求：

| 请求 | 主机 | 作用 |
|---|---|---|
| `GET /generate_204` | `connectivitycheck.gstatic.com` | 连通性探测 |
| `GET /cast/chromecast/device/stadiaconfig` | `clients3.google.com` | 拉取设备配置 |
| `POST /service/update2` | `update.googleapis.com` | Omaha 协议查固件更新 |
| `POST /log/batch` | `play.googleapis.com` | Clearcut 日志 |
| `POST /v1:FirmwareVersionCheck` | `cloudcast-pa.googleapis.com` | 版本校验 |
| `POST /v1:RegisterController` | 同上 | 注册，拿 `registration_token` |
| `POST /gmsg` | `cloudcast-gmsg-prod.googleapis.com` | 长轮询消息通道 |
| `POST /v1:DiscoverDisplay` | `cloudcast-pa.googleapis.com` | **控制器是 WebRTC offerer**，带 SDP offer |
| `POST /v1:ResolveDiscovery` | 同上 | 完成发现 |

TLS 校验有个关键弱点（对复刻极其有利）：固件内置 Google Trust Services 根证书，但**不校验主机名、不校验有效期、不校验吊销**，所以只要一张同根证书就能冒充所有 `*.googleapis.com`。

### 8.2 会话与数据面

- **GMsg**：控制器用 `display_token` 订阅，服务器推送 answer/ICE。
- **WebRTC**：控制器发 offer，接收端回 answer；STUN/DTLS 由接收端终结；DTLS 之后是自定义 RPC 握手，直到 READY。
- **输入报告**：READY 后每次变化上报，摇杆 -32768..32767，扳机 0..255，按键位按 XInput 布局。
- **音频**：Opus 推流到手柄 3.5 mm 耳麦口；麦克风可反向采集。
- **游戏会话**：`StartGame` 后开第二条会话，**只有这条会话能驱动震动马达**。

### 8.3 BLE 配网（首次开机/复位后）

手柄没有网络时会闪橙灯，广播 Fast Pair（`0xFE2C`）与配置服务 `0000fea0-…`：

| 特征值 | 用途 |
|---|---|
| `0328fe40-…` | 写入 `connect_to_network` JSON（SSID、加密方式、RSA 加密后的密码） |
| `0228fe40-…` | 写入设置 JSON，`{}` 触发 Wi-Fi 扫描 |
| `0c7c6160-…` | 配网状态（1 字节） |
| `0d7c6160-…` | 读取 IP |
| `127c6160-…` | OTA 状态 |

密码用控制器公钥做 **RSA PKCS#1 v1.5** 加密后 base64；`stadiacast-provision` 已实现完整流程。这一段对"想给手柄写自己的配网工具"的人价值极高。

### 8.4 其它 Wi-Fi 相关项目

- [helloparthshah/StadiaWireless](https://github.com/helloparthshah/StadiaWireless)：更早期的方案，手机浏览器 + 本地 server，把 Wi-Fi 手柄输入转发成虚拟手柄（已被 stadiacast 全面超越，但代码可读性好）。
- 早期 Reddit 用户 debianite 的帖子对刷机与 Wi-Fi 都有详细记录，被多个仓库引用为"刷机流程原始出处"。

> 注意：boot 到蓝牙固件后，Wi-Fi 栈被移除，第 8 节整套协议只对 gotham 固件有效。想同时保留两条路线，只能靠双槽（A/B）或重新刷写。

---

## 9. BootROM、HAB 与"到底能不能改固件"

### 9.1 安全启动链

i.MX RT1061 出厂配置为 **HAB 闭合（closed）**：BootROM 校验 IVT/CSF，只运行 Google 签名的镜像；flashloader 也是"受限版"，只放行刷机必需的少数命令和内存区域。所以：

- **不能**改现有固件再刷回去（签名不过）。
- **能**通过 SDP 载入 Google 签名的 flashloader，进而擦写 flash（官方刷机就是这么干的）。
- **能**在 OCRAM 里跑自定义代码吗？理论上 BootROM 在 HAB closed 下启用 MPU 限制执行区域——但有一个实现 bug。

### 9.2 tchebb 的 3 字节溢出（目前最强的突破口）

仓库：[codeberg.org/tchebb/nxp-sdp-overrun](https://codeberg.org/tchebb/nxp-sdp-overrun)

- BootROM 的 `sdp_hid_callback()` 把 HID 报告写进 `sdp_hid_request` 缓冲区时，**从 +3 偏移开始写**，最多溢出 3 字节。
- 紧邻的全局变量是 `sdp_dev`，其首字段是指向 `usb_device_struct_t` 的指针；溢出刚好覆盖该指针低 3 字节，可指向 `0x20xxxxxx`（DTCM/OCRAM 全域）。
- 该指针只被 `sdp_usb_pump()` 读取，所以损坏发生在当前传输结束之后，不会当场崩溃。
- 攻击者伪造 `usb_device_struct_t`、`epCallbacks`、EHCI 状态结构与寄存器，**一次 USB 传输**完成代码执行。
- 另一个"幸运的 bug"：`enable_mpu()` 配完所有 region 后**忘了真正使能 MPU**（使能代码只在"配置提前结束"分支里），所以 HAB closed 下也能执行 OCRAM 代码。

适用性：RT1060 BootROM，HAB 4.3.7；作者给出了完整符号地址与利用脚本。这套方法已被社区用于 Stadia 手柄的 RAM 代码实验（gomezluisj 的 `stadia-ram-hello` 就基于它，在 OCRAM 跑 USB CDC-ACM + 模拟 Switch Pro 手柄）。

### 9.3 已知 CVE

- **CVE-2022-45163**：NXP 多款 i.MX（含 RT1060）在 SDP 模式下的**信息泄露**，冷/热启动时可从 SDP 端口读出内存内容；官方缓解措施是用 eFUSE 彻底关闭 SDP。NCC Group 的分析见 [research.nccgroup.com](https://research.nccgroup.com/2022/11/17/cve-2022-45163/)。对逆向的意义：可以读内存，但不能直接执行代码。
- 两者结合看：SDP 既是官方刷机通道，也是攻击面；Google 的"受限 flashloader"本质上是在 CVE 之后做的收敛。

### 9.4 深度研究日志（谨慎使用）

[JaimeDelgadoNaya/stadia-controller-research](https://github.com/JaimeDelgadoNaya/stadia-controller-research) 用 90 多个"phase"记录了 HAB、CSF、SRC_GPR7、KVS、BEE 的静态审计，附带脚本与 SHA-256 证据链。优点是索引极全、可复现；缺点是大量结论是"未证明/待验证"，且行文有明显的自动化生成痕迹。**把它当"问题清单和证据库"，不要当结论来源。**

---

## 10. 使用层：驱动、平台与改造

### 10.1 Linux

- 内核 6.6+ 自带 `hid-google-stadiaff`（震动），输入走 `hid-generic` + SDL。
- udev 规则见 6 节；`/dev/hidraw*` 权限是刷机与自定义工具的常见坑。
- RetroArch/EmulationStation 可直接识别为 "Google Stadia Controller"。

### 10.2 Windows

| 方案 | 仓库 | 特点 |
|---|---|---|
| ViGEm 系 | [71/stadiacontroller](https://github.com/71/stadiacontroller) | 有线 → Xbox 360 手柄，支持震动与 Assistant/Capture 自定义命令；已停止维护 |
| StadiEm | [MWisBest/StadiEm](https://github.com/MWisBest/StadiEm) | C# 实现，支持 360/DS4 模拟，无官方构建 |
| WinStadia | [aisk/WinStadia](https://github.com/aisk/WinStadia) | 轻量，USB/蓝牙都能转 XInput |
| XOutput | [csutorasa/XOutput](https://github.com/csutorasa/XOutput) | 通用映射，不支持震动 |

**Windows 蓝牙模式没有震动**是普遍现象（BLE 协议栈差异），社区方案是加一个硬件中继（见 10.5）。

### 10.3 macOS / iOS

- macOS 原生 GameController 框架可直接识别 BLE 手柄。
- [0xWDG/GameControllerKit](https://github.com/0xWDG/GameControllerKit) 是 Swift 封装，含 Stadia 支持与灯效/震动 API。

### 10.4 Switch 与其它主机

- **8BitDo USB 无线适配器 2** 在 2023 年初宣布支持 Stadia 手柄，可接 Switch（[9to5Google 报道](https://9to5google.com/2023/02/03/stadia-controller-nintendo-switc/)）。
- Steam 在 2025-12 更新后无需开启"通用手柄支持"即可识别，Stadia 键 = Xbox 键，截图键可用（[9to5Google](https://9to5google.com/2025/12/11/steam-google-stadia-controller-support/)）。

### 10.5 硬件改造：把尸体变成资产

- **BLE 中继 dongle**：[berge472/stadia-ble-dongle](https://github.com/berge472/stadia-ble-dongle)（ESP32-S3，USB HID → BLE HID）。
- **CH582F/CH592F 超低成本方案**：[O-IceDawn-O/stadia-stick](https://github.com/O-IceDawn-O/stadia-stick)，¥6.8 核心板，BLE 连手柄、USB 出 SInput，**带回震动**与电量读取，中文 README 写得很细。
- **Tandem Mode 改造**：Stadia 手柄的 USB-C 可以串联第二只手柄（Tandem Mode），即使刷了蓝牙固件仍可用。Bringus Studios 把除 Home 外的按键全部拆掉，做成"有线手柄 → 蓝牙"的适配器（[Android Authority 报道](https://www.androidauthority.com/stadia-usb-adapter-3650163/)）。

---

## 11. 社区、讨论与中文资料

| 类型 | 链接 | 说明 |
|---|---|---|
| 主社区 | [reddit.com/r/Stadia](https://www.reddit.com/r/Stadia/) | 关服后仍有刷机、配对、拆机讨论；搜索 `controller bluetooth` |
| GitHub 主题 | [github.com/topics/stadia](https://github.com/topics/stadia) | 新项目基本都挂在这个 topic 下 |
| 中文视频/图文教程 | [B站 opus 教程](https://www.bilibili.com/opus/1209579308786384945) | "Stadia 谷歌退市手柄，B 站暂时最全的，完美激活和必要驱动下载教程" |
| 中文资讯 | [网易：谷歌在 Stadia 下线当天发布手柄蓝牙功能更新](https://www.163.com/dy/article/HREGKUNE0526D8LR.html) | 时间线背景 |
| 兼容性清单 | [pjburnhill/stadia-controller-support](https://github.com/pjburnhill/stadia-controller-support) | 各平台/设备支持情况汇总 |
| iFixit 中文 | [谷歌 Stadia 手柄打开过程](https://zh.ifixit.com/Guide/Google+Stadia+Controller+Opening+Procedure/143461) | 拆机步骤中文化 |

> 中文资料以"怎么用"为主，涉及协议/固件层面的内容几乎没有；深度技术仍集中在英文博客与 GitHub。Reddit、GitHub Raw、Google 文档等域名在境内通常需要代理，本文所有链接于 2026-11-25 逐一实测（返回 200 或可正常打开）。

---

## 12. 工具链清单

| 环节 | 工具 | 用途 |
|---|---|---|
| USB 抓包 | Wireshark + USBPcap（Win）/ usbmon（Linux） | 复现官方刷机流程，抓 control/bulk 传输 |
| HID 解析 | `usbhid-dump`、`hidrd-convert`、HID Explorer、`chrome://device-log` | 拿描述符、逐字节比对报告 |
| WebUSB/HID 实验 | Chrome DevTools 控制台 | 不改驱动直接发控制请求，验证协议 |
| 固件分析 | Ghidra（ARM Cortex-M）、IDA、`binwalk`、`strings` | 加载基址 `0x60040000` / `0x20000000` |
| flash 读取 | `flashrom` + PICkit 2 / CH341A + **1.8V 适配** | 拆片直读，最完整 |
| NXP 官方 | [MCUBootUtility](https://github.com/JayHeng/NXP-MCUBootUtility)（含 `sdphost`/`blhost`、FCB 生成器）、i.MX RT1060 参考手册 | SDP 命令、FlexSPI 配置、启动镜像制作 |
| 逻辑分析 | Saleae 或廉价 8 通道逻辑分析仪 | 抓 FlexSPI/QSPI 时序，验证 FCB |
| 硬件改造 | 恒温烙铁、热风台、1.8V LDO | 拆屏蔽罩、换 flash、飞线调试口 |

---

## 13. 建议的逆向路线图

**阶段 0：不拆机的观测（1 天）**

1. `lsusb` / 设备管理器记录各模式 VID:PID，对照第 4.2 节表格。
2. Chrome 打开 `chrome://device-log`，插拔手柄，看描述符与接口。
3. 用 Klay 镜像跑一遍官方刷机流程，Wireshark 全程抓包，得到"官方协议"的 ground truth。

**阶段 1：协议复刻（3–5 天）**

1. 用 WebHID 复刻第 7.2 节的输入报告解析，验证 Assistant/Capture 的位定义。
2. 跑 `stadiatool info`，对照抓包里的 `0x81/0x83/0x84` 控制请求。
3. 读 DJm00n 的 pcap，与自己的抓包对齐。

**阶段 2：固件静态分析（1–2 周）**

1. 下载 5.1 的 OTA（或 `stadiatool dump`），按第 4.4 节切分区。
2. Ghidra 以 `0x60040000` 为基址加载 Slot A，先看字符串与 RPC 表。
3. 对照 stadiacast 的 protobuf 字段表，找 `RegisterController`/`DiscoverDisplay` 的处理函数。

**阶段 3：动态执行（高风险，需硬件）**

1. 按 tchebb 的方法在 SDP 下跑 OCRAM 代码，先点灯/打串口，确认可控。
2. 再接 USB CDC，做内存读写与 flash 访问。
3. 想要"自定义固件"必须解决签名问题，目前公开资料里**没有**绕过 HAB 的完整方案。

**阶段 4：硬件层（可选）**

拆 flash 直读做全片备份，或用逻辑分析仪验证 FlexSPI 配置，为"换大容量 flash / 双系统"做准备。

---

## 14. 已知坑与风险

- **不可逆**：官方口径是刷蓝牙后不能回 Wi-Fi；社区回退工具依赖特定 gotham 镜像，并非所有批次验证过。
- **变砖点**：`dvt/pvt`、`dev/stage/prod` 不匹配；刷写中断电；用错 FCB 导致 flash 配置错误。
- **线材**：只有充电功能的 USB-C 线无法进入刷机模式。
- **1.8V**：flash 与部分测试点都是 1.8V，3.3V 编程器会烧片。
- **电池**：拆机时易刺穿；长期存放鼓包的手柄不要再充电。
- **版权与合规**：固件 bin 是 Google 版权作品；BootROM 漏洞利用属安全研究范畴，仅在自有设备上验证，注意当地法律（DMCA 反规避条款等）。
- **信息时效**：官方页面已下线，任何"官方工具"链接都应以第 6 节的镜像为准；本文标注的可用性为 2026-11-25 实测。

---

## 15. 一分钟速查

- 官方页死了 → 用 [christopherklay.github.io/stadiacontroller](https://christopherklay.github.io/stadiacontroller/)
- 想回退 Wi-Fi 固件 → [luigimannoni 刷机器](https://luigimannoni.github.io/stadia-controller-flasher/) + [vouiren/StadiaFW](https://github.com/vouiren/StadiaFW)
- 想读固件 → `stadiatool dump` 或拆 flash（1.8V！）
- 想懂刷机原理 → GaryOderNichts 博客
- 想懂 USB 协议 → Chrome WebHID 博客 + DJm00n 描述符
- 想懂 Wi-Fi 协议 → stadiacast `docs/protocol.md`
- 想跑自定义代码 → tchebb `nxp-sdp-overrun`
- Windows 没震动 → [stadia-stick](https://github.com/O-IceDawn-O/stadia-stick) 硬件中继
- 只想当手柄用 → Steam 直接认；Switch 用 8BitDo 适配器 2

---

## 16. 附录：全量下载的体积估算

以下数字为 2026-11-25 实测（GitHub API 的仓库体积、HTTP `Content-Length`、FCC 页面标注的文件大小），用于规划硬盘和流量。

| 类别 | 内容 | 体积 |
|---|---|---|
| 最小固件包 | gotham 282115 OTA（4.16 MB）+ bruce 量产固件（1.05 MB）+ flashloader（0.10 MB）+ 2 个 FCB（几十 KB） | **≈ 5.4 MB** |
| 关键仓库（4 个） | Scyne 固件备份 0.75 MB、GaryOderNichts 工具 0.01 MB、stadiacast 1.1 MB、Klay 刷机页 2.3 MB | **≈ 4.2 MB** |
| FCC 关键文档 | 内部照片 3.9 MB、外部照片 1.7 MB、原理图 0.8 MB、框图 0.7 MB、工作原理 0.6 MB、用户手册 0.1 MB | **≈ 7.8 MB** |
| 全部 21 个 GitHub 仓库 | 含重复固件；最大的是 vouiren/StadiaFW 22.8 MB、StadiaMemories 14.1 MB、luigimannoni 6.5 MB、hazrpg 5.3 MB | **≈ 63 MB** |
| NXP 文档与工具 | i.MX RT1060 参考手册 PDF ≈ 55 MB；MCUBootUtility 仓库 ≈ 68 MB（含 sdphost/blhost 与 FCB 生成器） | **≈ 123 MB** |
| 工具可执行文件 | stadiacast：Windows 36 MB / macOS 35 MB / Linux 66 MB（另有 245 KB 的 wheel） | **36–100 MB** |
| 自行 dump 的整片 flash | 每台 16 MiB | **16 MB / 台** |

按用途汇总：

- **只求"能刷机、能查协议"**：约 15–20 MB（最小固件包 + 4 个关键仓库 + FCC 内照）。
- **文字、固件、代码全收**：约 80 MB（全部 GitHub 仓库 + FCC + 最小固件包，去重后更少）。
- **再加 NXP 手册与工具链**：约 200 MB。
- **再加各平台可执行文件、拆机视频**：300 MB – 1 GB。

两点说明：GitHub zipball 的实际体积与 API 给出的仓库体积有 ±20% 偏差；同一份 bruce/gotham 固件在 5–6 个仓库里重复出现，去重后可省 20 MB 左右。
