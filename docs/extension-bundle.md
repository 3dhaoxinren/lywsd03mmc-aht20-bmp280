# R2 extension-only bundle

这是新增扩展，不是可直接刷入设备的完整固件。

解压后，在当前目录运行（Python 3.12+、curl）：

```powershell
python fetch_inputs.py
python apply_r2.py inputs/original_0130.bin extension.bin patch_manifest.json R2.bin
```

必须输出 96436 字节且 SHA256 为：

```text
8beab84985aba525b11101af9614f34c663e703bf2153416b53c981e3620e34b
```

包内 `extension.bin` 不含整份原厂固件，**不能直接刷写**。脚本验证原版、打补丁并验证最终 R2 哈希；任何不匹配都会在输出前报错。`SHA256SUMS` 用于核对包内文件完整性。

原版 OTA 从 PVVX 固定提交公开存档下载，其版权不属于本项目 MIT 范围。

文件恢复：

```powershell
python restore_ota.py R2.bin recovered_0130.bin
```

只恢复文件，不恢复设备个体密钥，也不操作硬件。刷写前备份整片 Flash、准备恢复通道；仅支持 HW B2.0 / 原厂 0130。传感器来源和实际气压尚未单独验证，详见：

https://github.com/3dhaoxinren/lywsd03mmc-aht20-bmp280
