# 虚拟面试官项目使用说明

本项目面向东南大学 AI+ 创新应用大赛，目标是构建一个可实时对话、可基于简历追问、可生成面试复盘和能力树的虚拟面试官。

当前版本是本地优先的 MVP：

- 前端：React + Vite。
- 后端：FastAPI + WebSocket。
- 语音链路：浏览器麦克风 -> 16 kHz PCM -> 后端 -> 阿里百炼 Qwen-Omni-Realtime。
- 文本链路：可配置为本地低成本追问，或调用阿里百炼文本模型。
- 复盘链路：生成模拟面试报告和能力树原型。

## 目录结构

```text
apps/web/                 前端应用
services/api/             FastAPI 后端
services/api/.env.example 百炼配置模板，不包含密钥
docs/issues.md            已发现问题、根因和解决方案记录
docs/unresolved-issues.md 当前未解决问题
docs/progress.md          项目进度记录
data/job_descriptions/    岗位 JD 示例
data/profiles/            本地私有简历资料，默认不提交 Git
```

## 环境要求

- Windows PowerShell
- Python 3.11+
- Node.js 18+
- 阿里云百炼 / DashScope API Key

## 后端配置

进入后端目录：

```powershell
cd <project-root>\services\api
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
```

复制环境变量模板：

```powershell
Copy-Item .env.example .env
notepad .env
```

在 `.env` 中填写：

```env
DASHSCOPE_API_KEY=你的百炼APIKey
REALTIME_MODE=bailian
BAILIAN_REALTIME_MODEL=qwen3.5-omni-plus-realtime
BAILIAN_REALTIME_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
TEXT_MODE=bailian_text
BAILIAN_TEXT_MODEL=qwen3.6plus
BAILIAN_TEXT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

说明：

- `REALTIME_MODE=bailian`：启用百炼实时链路。
- `REALTIME_MODE=mock`：离线开发模式，不调用阿里模型。
- `TEXT_MODE=bailian_text`：文本框输入会调用百炼文本模型。
- `TEXT_MODE=local`：文本框输入只走本地低成本面试官，不产生文本模型费用。
- 如果 `qwen3.6plus` 在你的百炼账号中不可用，请把 `BAILIAN_TEXT_MODEL` 改成控制台中已开通的 Qwen 文本模型。

启动后端：

```powershell
cd <project-root>\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

正常结果：

```json
{"status":"ok"}
```

## 前端启动

```powershell
cd <project-root>\apps\web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

## 日常启动命令

终端 1，启动后端：

```powershell
cd <project-root>\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

终端 2，启动前端：

```powershell
cd <project-root>\apps\web
npm run dev -- --host 127.0.0.1 --port 5173
```

## 使用流程

1. 打开 `http://127.0.0.1:5173/`。
2. 点击 `开始面试`。
3. 点击 `连接面试官`。
4. 文本模式：
   - 在文本框中输入回答。
   - 点击 `发送模拟回答`。
   - 如果 `TEXT_MODE=bailian_text`，后端会调用百炼文本模型。
   - 如果 `TEXT_MODE=local`，后端会使用本地低成本追问逻辑。
5. 语音模式：
   - 点击 `开始麦克风`。
   - 浏览器会请求麦克风权限。
   - 前端采集 16 kHz PCM 音频并发送给后端。
   - 后端转发给 Qwen-Omni-Realtime。
6. 点击 `结束并生成报告`，查看模拟报告和能力树原型。

## 当前模式说明

| 输入方式 | 当前链路 | 成本特点 | 说明 |
| --- | --- | --- | --- |
| 文本输入 | 百炼文本模型或本地回退 | 低于实时语音 | `TEXT_MODE=bailian_text` 调用文本模型，失败时本地回退 |
| 麦克风 | Qwen-Omni-Realtime | 实时模型费用 | 需要浏览器麦克风权限和有效 API Key |
| 复盘报告 | 本地确定性原型 | 无外部模型费用 | 后续可升级为模型评分 + RAG 证据引用 |

## 验证命令

后端测试：

```powershell
cd <project-root>\services\api
.\.venv\Scripts\pytest -q
```

前端构建：

```powershell
cd <project-root>\apps\web
npm run build
```

## 修改 `.env` 后重启后端

如果 `8000` 端口已被旧后端占用：

```powershell
$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $listeners) {
  $ownerPid = $conn.OwningProcess
  Stop-Process -Id $ownerPid -Force
}

cd <project-root>\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 隐私与安全

- 不要提交 `services/api/.env`。
- 不要提交真实 API Key。
- 不要提交未经脱敏的简历、证书、个人资料。
- `data/profiles/` 下的本地私有资料默认被 Git 忽略。

## 常见问题

### 1. 文本输入没有调用模型怎么办？

检查 `.env`：

```env
TEXT_MODE=bailian_text
BAILIAN_TEXT_MODEL=qwen3.6plus
```

然后重启后端。如果页面出现 `Bailian text call failed`，优先检查模型名是否在你的百炼账号中可用。

### 2. 页面先出现 realtime 错误，但文本还能回复，正常吗？

正常。实时语音和文本模型是两条链路。当前实现中，如果 Qwen-Omni-Realtime 连接失败，文本模式仍然可以继续调用百炼文本模型或本地回退。

### 3. 麦克风没声音或没有模型回复怎么办？

先确认浏览器麦克风权限，然后检查阿里控制台是否有实时模型调用记录。语音链路仍需要更多真机验证，当前未解决项记录在 `docs/unresolved-issues.md`。
