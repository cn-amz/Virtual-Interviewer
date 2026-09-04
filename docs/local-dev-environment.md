# 本地开发环境与启动记录

更新时间：2026-07-03

本文记录 Codex 当前实际使用的本地运行环境、启动命令、端口和排查入口，避免只凭口头说明复现服务。

## 当前 Codex 运行环境

- 工作目录：`<project-root>`
- Git 分支：`codex/virtual-interviewer-mvp`
- 操作系统：Windows 11 家庭版 中文版
- PowerShell：`5.1.26100.8655`
- 系统 Python：`Python 3.11.7`
- 后端虚拟环境 Python：`Python 3.11.7`
- Node.js：`v24.14.0`
- npm：`11.9.0`

后端应使用 `services\api\.venv` 中的 Python 启动，并从 `services\api` 读取配置。

## 当前服务端口

- 后端 API：`http://127.0.0.1:8000`
- 前端页面：`http://127.0.0.1:5173/`
- 后端健康检查：`http://127.0.0.1:8000/api/health`

启动成功时，健康检查应返回：

```json
{"status":"ok"}
```

## 当前 `.env` 配置摘要

配置文件位置：`<project-root>\services\api\.env`

敏感值不要提交到 Git。当前记录只保留非敏感项：

```text
DASHSCOPE_API_KEY=<redacted>
REALTIME_MODE=bailian
BAILIAN_REALTIME_MODEL=qwen3.5-omni-plus-realtime
BAILIAN_REALTIME_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
TEXT_MODE=bailian_text
BAILIAN_TEXT_MODEL=qwen3.6-plus
BAILIAN_TEXT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## 推荐启动方式

打开两个 PowerShell 窗口。

窗口 1，启动后端：

```powershell
Set-Location -LiteralPath '<project-root>'
.\scripts\dev.ps1 backend
```

窗口 2，启动前端：

```powershell
Set-Location -LiteralPath '<project-root>'
.\scripts\dev.ps1 frontend
```

如果 PowerShell 阻止脚本执行，可以使用：

```powershell
powershell -ExecutionPolicy Bypass -File '<project-root>\scripts\dev.ps1' backend
powershell -ExecutionPolicy Bypass -File '<project-root>\scripts\dev.ps1' frontend
```

## Codex 本次后台启动方式

Codex 在 2026-07-03 使用后台进程启动了服务，并把日志写到：

- 后端标准输出：`<project-root>\logs\backend.out.log`
- 后端错误输出：`<project-root>\logs\backend.err.log`
- 前端标准输出：`<project-root>\logs\frontend.out.log`
- 前端错误输出：`<project-root>\logs\frontend.err.log`

后台启动命令等价于：

```powershell
Set-Location -LiteralPath '<project-root>\services\api'
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

```powershell
Set-Location -LiteralPath '<project-root>\apps\web'
npm run dev -- --host 127.0.0.1 --port 5173
```

## 查看当前端口进程

```powershell
foreach ($port in 8000,5173) {
  $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($conn in $listeners) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)"
    "$port -> PID=$($conn.OwningProcess) $($process.Name) $($process.CommandLine)"
  }
}
```

## 停止服务

如果服务是前台窗口启动的，直接在对应 PowerShell 窗口按 `Ctrl+C`。

如果服务是后台进程启动的，可以按端口停止：

```powershell
foreach ($port in 8000,5173) {
  $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  foreach ($conn in $listeners) {
    Stop-Process -Id $conn.OwningProcess -Force
  }
}
```

## 登录与试用

打开：

```text
http://127.0.0.1:5173/
```

演示账号：

```text
用户名：demo
密码：demo123456
```

流程：

1. 登录后进入 Dashboard。
2. 点击 `开始模拟面试`。
3. 在设置页点击 `开始模拟面试`。
4. 点击 `连接面试官`。
5. 文本模式可直接点击 `发送模拟回答`。
6. 语音模式需要点击 `开始麦克风`，并在浏览器或系统弹窗中允许麦克风权限。

## 常见问题

- 修改 `services\api\.env` 后，需要重启后端。
- 前端页面改动通常刷新浏览器即可；如果 Vite 已停止，需要重启前端。
- 如果 `8000` 或 `5173` 被占用，先用“查看当前端口进程”确认占用者。
- 麦克风只能在 `localhost`/`127.0.0.1` 或 HTTPS 场景可靠调用；公网演示需要 HTTPS 或可信内网穿透方案。
