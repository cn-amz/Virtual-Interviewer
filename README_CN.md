# Virtual Interviewer 虚拟面试官

[English](README.md) | 简体中文

Virtual Interviewer 是一个本地优先的 AI 模拟面试应用。它可以根据候选人简历和岗位 JD 组织实时面试，在面试结束后保存对话证据、生成分析报告，并持续整理个人能力树。

项目目前处于可运行的 MVP 阶段，推荐使用阿里云百炼 API 路径。MiniCPM-o 本地全双工语音路径已完成接口接入，但模型部署成本较高，仍作为实验能力保留。

## 功能概览

| 功能 | 当前能力 |
| --- | --- |
| 面试资料管理 | 上传 PDF 或 DOCX 简历；粘贴或上传 Markdown 岗位 JD |
| 面试前配置 | 选择模型提供方、候选人、简历和目标岗位，并检查模型就绪状态 |
| 实时语音面试 | 浏览器采集 16 kHz PCM 音频，通过 FastAPI WebSocket 接入百炼 Qwen-Omni-Realtime |
| 文本面试 | 可使用百炼文本模型追问，也可配置本地确定性回退 |
| JD 约束提问 | 将所选 JD 正文、岗位重点和追问策略注入面试上下文 |
| 会话证据 | 保存稳定轮次 ID、候选人与面试官文字、结束状态和紧凑音频统计 |
| 面试报告 | 根据持久化对话生成总结、评分、优势和待提升项，模型失败时保留确定性回退 |
| 历史记录 | 查看已经完成且包含有效候选人回答的历史报告 |
| 个人能力树 | 按能力类型、问题、回答证据和待提升方向组织长期面试记录，并可导出 Obsidian Markdown |

## 技术栈

- 前端：React、TypeScript、Vite、Vitest
- 后端：FastAPI、Pydantic、WebSocket、pytest
- 实时模型：阿里云百炼 Qwen-Omni-Realtime，或实验性的 MiniCPM-o 本地服务
- 文本模型：阿里云百炼兼容 OpenAI 的文本接口
- 本地存储：JSON 会话账本、报告、JD 分析和能力树 Markdown

## 项目结构

```text
apps/web/                         React 前端
services/api/                     FastAPI 后端
services/api/.env.example         环境变量模板，不包含密钥
scripts/                          Windows 一键启动与停止脚本
data/interview_profiles/          面试 Profile 与简历，默认不提交 Git
data/interview_job_descriptions/  岗位 JD 与分析结果，默认不提交 Git
data/interviews/                  面试账本和报告，默认不提交 Git
data/ability_graphs/              能力树 JSON 与 Markdown，默认不提交 Git
docs/                             架构、配置、问题和开发记录
```

## 推荐运行方式：百炼 API

### 环境要求

- Windows 10/11 与 PowerShell
- Python 3.11 或更高版本
- Node.js 18 或更高版本
- 已开通模型权限的阿里云百炼 API Key

### 1. 克隆项目

```powershell
git clone https://github.com/cn-amz/Virtual-Interviewer.git
Set-Location -LiteralPath '.\Virtual-Interviewer'
```

### 2. 生成配置文件

在仓库根目录双击 `start-api.cmd`，或在 PowerShell 中运行：

```powershell
.\start-api.cmd
```

首次运行会从 `.env.example` 创建 `services/api/.env`，然后提示填写百炼 API Key。

### 3. 配置百炼 API

```powershell
notepad .\services\api\.env
```

至少确认以下配置：

```env
DASHSCOPE_API_KEY=替换为你的百炼APIKey
REALTIME_MODE=bailian
BAILIAN_REALTIME_MODEL=qwen3.5-omni-plus-realtime
BAILIAN_REALTIME_URL=wss://dashscope.aliyuncs.com/api-ws/v1/realtime
TEXT_MODE=bailian_text
BAILIAN_TEXT_MODEL=qwen3.6-plus
BAILIAN_TEXT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

模型名称必须以你的百炼账号实际开通列表为准。完整配置与排障说明见 [百炼 API 配置指南](docs/bailian-api-setup.md)。

### 4. 启动前后端

再次运行：

```powershell
.\start-api.cmd
```

脚本会：

1. 检查 API 配置，但不会输出密钥。
2. 创建后端虚拟环境并安装缺失依赖。
3. 安装前端依赖。
4. 启动后端 `http://127.0.0.1:8000`。
5. 启动前端并打开 `http://127.0.0.1:5173/`。

停止由脚本启动的服务：

```powershell
.\stop-api.cmd
```

API 模式不需要 Docker，也不会启动 MiniCPM-o。

## 首次准备面试资料

仓库不会包含任何真实简历、候选人资料或面试记录。登录后从工作台进入“简历与岗位 JD”：

1. 使用一个 Profile ID 上传 PDF 或 DOCX 简历。旧版 DOC 可以存档，但不能提取为模型上下文。
2. 粘贴岗位职责和任职要求，或上传 UTF-8 Markdown JD。
3. 可点击“AI 分析面试重点”生成岗位方向、关注点和追问策略。
4. 返回面试配置页，选择模型、Profile、简历和 JD 后开始面试。

当前版本还要求每个 Profile 目录包含两个文本文件：

```text
data/interview_profiles/<profile-id>/prompt.txt
data/interview_profiles/<profile-id>/qa_bank.md
```

`prompt.txt` 用于候选人背景和面试上下文，`qa_bank.md` 用于候选人已有问答材料。上传简历暂时不会自动创建这两个文件，这是已登记的首次使用问题。

## 使用流程

1. 打开 `http://127.0.0.1:5173/`。
2. 使用演示账号登录：用户名 `demo`，密码 `demo123456`。
3. 在“简历与岗位 JD”中准备面试资料。
4. 点击“开始模拟面试”，选择百炼 API 或 MiniCPM 本地模式。
5. 选择 Profile、简历和目标 JD，等待引擎状态显示为可用。
6. 进入面试后连接面试官，再开启麦克风或发送文字回答。
7. 可以退出面试而不生成报告，也可以结束并等待会话持久化后生成报告。
8. 从工作台查看历史报告、个人能力树或导出的 Obsidian Markdown。

## 运行模式

| 模式 | 配置或入口 | 适用场景 | 当前状态 |
| --- | --- | --- | --- |
| 百炼实时语音 | 面试前选择“百炼 API” | 推荐体验、比赛演示 | 主路径 |
| 百炼文本追问与报告 | `TEXT_MODE=bailian_text` | 文本回答、JD 分析、报告生成 | 主路径，失败时本地回退 |
| 本地文本回退 | `TEXT_MODE=local` | 不调用文本模型的开发测试 | 可用，但策略较简单 |
| MiniCPM-o 本地语音 | 面试前选择“MiniCPM 本地” | 本地模型研究 | 实验性，需要单独启动兼容服务 |

MiniCPM-o 不包含在一键 API 启动流程中。默认地址是 `wss://127.0.0.1:8006`，只有状态接口返回模型空闲时，前端才允许创建会话。

## 手动启动

后端：

```powershell
Set-Location -LiteralPath '.\services\api'
python -m venv .venv
.\.venv\Scripts\pip.exe install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

前端需要在另一个从仓库根目录打开的终端中启动：

```powershell
Set-Location -LiteralPath '.\apps\web'
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

后端健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

正常结果为 `{"status":"ok"}`。

## 测试与构建

后端测试：

```powershell
Set-Location -LiteralPath '.\services\api'
.\.venv\Scripts\python.exe -m pytest -q
```

前端测试与生产构建：

```powershell
Set-Location -LiteralPath '.\apps\web'
npm test -- --run
npm run build
```

API 启动条件检查：

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-api.ps1 -Check
```

## 数据与隐私

- 不要提交 `services/api/.env` 或任何真实 API Key。
- 不要提交未经脱敏的简历、证书、个人资料或面试记录。
- `data/interview_profiles/`、`data/interview_job_descriptions/`、`data/interviews/` 和 `data/ability_graphs/` 默认由 Git 忽略。
- JD 分析结果保存为对应 JD 的 `*.analysis.json`，面试报告和能力树均保留到本地数据目录。
- 当前演示账号只适合本地运行；后端尚未按公网多用户部署要求完成鉴权隔离。

## 当前边界

- 实时语音的停顿判定和气声过滤仍需针对真实麦克风继续校准。
- 问题覆盖目前偏向项目深挖和工程实践，基础知识与岗位匹配度的配额仍需加强。
- 报告评分、能力树分支和待提升项仍需进一步绑定逐条对话证据。
- JD 分析结果已经保存，但历史分析的再次查看入口还不完整。
- MiniCPM-o 对显存、磁盘读取和冷启动时间要求较高。

完整问题清单见 [当前未解决问题](docs/unresolved-issues.md)，问题发现和修复过程见 [问题记录](docs/issues.md)。

## 相关文档

- [百炼 API 配置指南](docs/bailian-api-setup.md)
- [项目架构方案](docs/architecture-proposal.md)
- [代码图谱](docs/codegraph.md)
- [补充功能与可行性分析](docs/supplemental-function-feasibility.md)
- [本地开发环境](docs/local-dev-environment.md)
- [项目进度](docs/progress.md)

## 开源许可

本项目采用 [MIT License](LICENSE) 开源。
