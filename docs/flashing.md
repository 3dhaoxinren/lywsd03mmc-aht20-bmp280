# 实验固件刷写

仅针对原厂 1.0.0_0130 / HW B2.0。先备份整片 Flash 和个体绑定信息，准备 SWS 恢复。这里不提供未经确认的全片擦写命令。

1. 构建 R2，核对 SHA256 和文件大小 96436 字节。不要使用 R1。
2. 断开其他手机/网关的主动连接，用 Chrome/Edge 打开 [TelinkMiFlasher](https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html)，Connect 选择 LYWSD03MMC。
3. 原厂设备需认证。使用现有 Device known id / Mi Token / Mi Bind Key 登录，可以避免主动重新注册。**Do Activation 会改变绑定状态，之后可能需要重新绑定米家**；不是只读密钥提取。不要公开这些字段。
4. 在 Select Firmware 选择本地 `...EXPERIMENTAL_R2.bin`。不要点网页推荐的 ATC/Zigbee/Original 按钮，那不是此驱动补丁。
5. 网页校验通过、日志明确登录成功后 Start Flashing；保持设备靠近电脑、页面打开、电池供电稳定。等明确完成，不要中途断电。
6. OTA 完成不等于新驱动已启动。先验证屏幕刷新、重新连接蓝牙；再只改变外接小板的环境，与原 U1 分开，验证数据来源。版本字符串仍为 0130，不能用于判断刷入哪个镜像。
7. 关闭刷机网页蓝牙连接后再测试米家。若做过网页激活，旧绑定可能失效；必要时移除旧设备、重新添加。不要接受米家自动升级原厂固件，否则会覆盖补丁。

## 常见日志

- `Invalid size pointer in Telink OTA binary firmware!`：文件头长度/对齐不合要求。R1 已重现此错误；R2 已通过网页原始函数离线校验。文件选择阶段尚未写设备。
- `Login successful`：认证成功，不证明传感器驱动有效。
- `Repeat login!`：网页按已登录处理，不是传感器或刷写失败的证据。
- `Update done ... / Disconnected`：工具报告 OTA 完成后断开，仍需确认设备重启、测量及米家工作。

不要为解决读数问题反复点击激活。先保留 U1；检查 GPIO 连线、供电、传感器地址和数据来源。没有实物总线波形或读数来源对照，不应宣称驱动硬件测试全部通过。

## 恢复

`restore_ota.py` 只把精确匹配的补丁 **文件** 恢复成公开原版 OTA，不会操作硬件，也不会恢复设备个体密钥。若设备还能 BLE OTA，可通过经过确认的 OTA 路径恢复原版；若不能启动，需使用事先准备并核对的 SWS 通道与设备备份。不要把 OTA 文件当作完整 Flash 转储。
