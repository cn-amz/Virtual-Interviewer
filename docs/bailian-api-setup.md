# 百炼 API 配置与一键启动

本文面向首次下载项目的 Windows 用户。API 模式只需要 Python、Node.js 和阿里云百炼 API Key，不需要 Docker，也不会启动 MiniCPM。

## 1. 环境要求

- Windows 10/11。
- Python 3.11 或更高版本，并可通过 `python.exe` 调用。
- Node.js 18 或更高版本，并可通过 `npm.cmd` 调用。
- 已开通阿里云百炼模型服务。

## 2. 获取 API Key

在[阿里云百炼控制台获取 API Key](https://help.aliyun.com/zh/model-studio/get-api-key/)。API Key 属于后端凭据，不要放进前端代码、截图或 Git 提交。

不同地域的 API Key 和服务地址不能混用。本项目默认使用中国内地地址：

```text
wss://dashscope.aliyuncs.com/api-ws/v1/realtime
https://dashscope.aliyuncs.com/compatible-mode/v1
```

子业务空间还需要确认对应空间已经获得目标模型权限，参考[子业务空间模型调用说明](https://help.aliyun.com/zh/model-studio/model-calling-in-sub-workspace)。

## 3. 配置项目

第一次双击根目录的 `start-api.cmd` 时，如果配置文件不存在，脚本会创建：

```text
services/api/.env
```

打开该文件，将第一行替换为真实 Key：

```env
DASHSCOPE_API_KEY=sk-你的真实Key
REALTIME_MODE=bailian
BAILIAN_REALTIME_MODEL=qwen3.5-omni-plus-realtime
BAILIAN_REALTIME_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
TEXT_MODE=bailian_text
BAILIAN_TEXT_MODEL=qwen3.6-plus
BAILIAN_TEXT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

配置含义：

| 配置 | 作用 |
| --- | --- |
| `REALTIME_MODE=bailian` | 语音面试使用百炼实时模型 |
| `TEXT_MODE=bailian_text` | 文字回答使用百炼文本模型 |
| `TEXT_MODE=local` | 文字回答使用本地规则追问，减少文本 API 费用 |
| `BAILIAN_REALTIME_MODEL` | 实时语音模型名称 |
| `BAILIAN_TEXT_MODEL` | JD 分析、文字追问和报告分析使用的文本模型 |

如果模型名称在当前账号不可用，请替换为百炼控制台中已经开通的兼容模型。修改 `.env` 后需要重启后端。

## 4. 一键启动与停止

双击项目根目录：

```text
start-api.cmd
```

脚本会依次完成：

1. 校验 `.env` 和百炼 API 模式。
2. 首次运行时创建 Python 虚拟环境并安装后端依赖。
3. 首次运行时安装前端依赖。
4. 在后台启动 API 和前端。
5. 等待健康检查通过并打开 `http://127.0.0.1:5173/`。

已经健康运行的 `8000` 和 `5173` 服务会被复用。启动日志位于：

```text
logs/backend.out.log
logs/backend.err.log
logs/frontend.out.log
logs/frontend.err.log
```

停止由脚本启动的服务：

```text
stop-api.cmd
```

停止脚本只处理本次项目记录的进程，不会按端口结束其他程序。

仅检查配置和已安装依赖，不启动服务：

```powershell
pwsh.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-api.ps1 -Check
```

## 5. 手动启动

后端：

```powershell
Set-Location .\services\api
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

前端另开一个终端：

```powershell
Set-Location .\apps\web
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

正常返回：

```json
{"status":"ok"}
```

## 6. 使用 JD-Grounded Prompt Orchestration

本项目将岗位化面试机制命名为 **JD-Grounded Prompt Orchestration（基于岗位描述的提示词编排）**，核心步骤是 **JD Grounding（岗位描述约束注入）**。

1. 在“数据管理”中粘贴或上传 Markdown 格式的 JD。
2. 可选执行“AI 分析面试重点”，生成岗位方向、关注点和追问策略。
3. 在面试配置页选择候选人、简历和 JD。
4. 开始面试后，百炼会始终收到受限长度的 JD 原文；已有分析会作为额外结构化约束使用。

因此即使岗位分析超时或尚未运行，面试仍会基于所选 JD。预分析是质量增强项，不是开始面试的前置条件。

## 7. 常见问题

### 提示 API Key 未配置

确认文件是 `services/api/.env`，变量名必须是 `DASHSCOPE_API_KEY`，并且没有保留模板占位值。

### 返回 401 或 403

检查 Key 是否有效、Key 所属地域是否与接口地址一致，以及业务空间是否获得模型调用权限。不要把长期 API Key 直接发送给浏览器。

### 模型不存在或没有权限

在百炼控制台确认实时模型和文本模型名称，然后修改 `.env` 中对应配置。

### 连接或分析超时

先查看 `logs/backend.err.log`。网络代理、地域地址、模型冷启动和账号限流都可能导致超时；文字链路失败时应用会保留可见错误并使用本地追问回退。

### 端口被占用

脚本不会结束未知进程。先检查 `8000` 或 `5173` 的占用程序并手动处理，再重新运行。
