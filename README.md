# RoutePilot — Windows 可视化路由管理器

RoutePilot 是一个使用 PyQt6 编写的 Windows 路由管理工具。它通过 Windows 自带的 `NetTCPIP` PowerShell 模块读取和修改系统配置，不解析受系统语言影响的 `route print` 文本。

## 功能

- 读取物理、虚拟和隐藏的 Windows 网络适配器，显示连接状态、接口索引、IP、MAC、链路速度和接口跃点。
- 分别读取临时路由（仅存在于 `ActiveStore`）和永久路由（存在于 `PersistentStore`）。
- 对临时路由进行新增、编辑和删除；重启后临时路由自动清除。
- 对永久路由进行新增、编辑和删除；变更同时作用于当前活动路由和永久存储。
- 支持 IPv4、IPv6、搜索、协议族过滤和表格排序。
- 网络操作在后台线程中执行，不阻塞界面。
- 默认最大化启动；按 `F11` 可进入真正的全屏模式，按 `Esc` 返回最大化窗口。
- 启动时自动请求管理员权限，路由写操作带有确认、输入校验和替换失败回滚。

## 环境要求

- Windows 10 或 Windows 11
- Python 3.10 或更高版本
- Windows PowerShell 5.1 和 `NetTCPIP` 模块（Windows 10/11 默认提供）

## 安装与启动

推荐使用独立虚拟环境：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

也可以双击 `run.bat`。程序启动时会出现 Windows UAC 提示，这是修改系统路由所必需的。只做界面开发或只读调试时，可运行：

```powershell
python main.py --no-elevate
```

## 使用说明

1. 在“网络适配器”页确认要使用的出口接口和接口索引。
2. 进入“临时路由”或“永久路由”，点击“新增路由”。
3. 目标网络使用 CIDR 格式，例如 `10.20.0.0/16`。如果输入 `10.20.1.5/16`，程序会自动规范为 `10.20.0.0/16`。
4. 下一跳填写网关 IP；IPv4 直连路由填 `0.0.0.0`，IPv6 直连路由填 `::`。
5. 从列表中选择出口适配器并设置路由跃点。Windows 会把路由跃点与接口跃点相加，综合值较小的路径通常优先。
6. 选中表格中的路由后可编辑或删除；双击路由可快速进入编辑窗口。

> 修改默认路由、VPN 路由或正在使用的远程连接路由可能立即中断网络。操作前请确认仍有本地恢复手段。

## 开发与测试

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q main.py route_manager
```

测试不会修改本机路由；路由命令测试使用假 PowerShell 执行器。

## 打包为 EXE

安装开发依赖后运行：

```powershell
pyinstaller --noconfirm --clean --windowed --name RoutePilot main.py
```

生成文件位于 `dist\RoutePilot\RoutePilot.exe`。启动 EXE 时仍会由程序主动请求管理员权限。

## 项目结构

```text
main.py                       启动、平台检查与 UAC 提权
route_manager/admin.py        Windows 管理员权限处理
route_manager/powershell.py   PowerShell 安全执行与 JSON 解码
route_manager/service.py      网卡/路由读取和增删改业务逻辑
route_manager/models.py       数据模型
route_manager/validation.py   IPv4/IPv6 与 CIDR 校验
route_manager/main_window.py  主窗口、导航与异步任务
route_manager/dialogs.py      路由编辑对话框
route_manager/widgets.py      页面、表格模型与筛选器
route_manager/theme.py        全局视觉主题
tests/                        不触碰系统路由的单元测试
```

## 实现说明

`New-NetRoute` 的 `PersistentStore` 参数不能用于直接创建永久路由。按 Microsoft 的接口约定，创建永久路由时不传 `PolicyStore`，Windows 会同时写入 `ActiveStore` 和 `PersistentStore`；创建临时路由时显式传入 `ActiveStore`。读取时，RoutePilot 用永久路由的目标、接口和下一跳标识从活动列表中剔除永久副本，从而得到真正的临时列表。

- [New-NetRoute 官方文档](https://learn.microsoft.com/powershell/module/nettcpip/new-netroute)
- [Get-NetRoute 官方文档](https://learn.microsoft.com/powershell/module/nettcpip/get-netroute)
- [Set-NetRoute 官方文档](https://learn.microsoft.com/powershell/module/nettcpip/set-netroute)
- [Remove-NetRoute 官方文档](https://learn.microsoft.com/powershell/module/nettcpip/remove-netroute)

