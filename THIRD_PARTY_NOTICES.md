# 第三方内容说明

本项目原创代码采用 MIT License 发布。以下第三方内容仍受各自许可证约束。

## Font Awesome Free 6.5.2

- 使用内容：应用图标中的 biohazard 图形
- 来源：https://fontawesome.com
- 图标许可证：Creative Commons Attribution 4.0 International（CC BY 4.0）
- 版权：Copyright 2024 Fonticons, Inc.
- 许可证全文：https://creativecommons.org/licenses/by/4.0/

应用图标中的其他图形、配色与容器样式由本项目制作。

## 7-Zip

- 随 Windows 发布包分发的组件：`7z.exe`、`7z.dll` 及安装包内附带的完整命令行文件
- 来源：https://www.7-zip.org/
- 许可证：GNU LGPL v2.1 及 7-Zip 许可证中的 unRAR 限制
- 许可证全文：发布包内 `_internal/7zip/License.txt`
- 版权：Copyright (C) 1999-2026 Igor Pavlov

构建脚本只从 7-Zip 官方下载页或官方 GitHub 发布仓库获取 x64 MSI，并在解包前核对官方发布页给出的 SHA-256。

## L4D2 Mod Manager 分类白名单

- 文件：`app/core/classify_data.py`
- 参考项目：https://github.com/fdklgbh/L4D2-Mod-Manager
- 上游许可证：GNU General Public License v3.0（GPL-3.0）
- 许可证全文：https://www.gnu.org/licenses/gpl-3.0.html

该分类白名单由上游项目的分类数据表转换而来，不属于本项目 MIT 授权范围；
其使用与再分发应遵循 GPL-3.0。项目其余原创代码不受此条约束。
