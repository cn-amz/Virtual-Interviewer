# 虚拟面试官代码整体架构提案

更新时间：2026-06-23

## 设计结论

第一版采用 Web App + Python 后端。

- 前端负责麦克风/摄像头采集、虚拟面试官 UI、实时字幕、复盘报告展示。
- 后端负责保护百炼 API Key、连接 Qwen-Omni-Realtime、工具调用、RAG、评分、能力树更新。
- 实时通话主链路走 Qwen-Omni-Realtime，优先 WebSocket；WebRTC 作为低延迟增强预留。
- 公网访问、内网穿透、正式站点申请/备案放到部署层，不进入业务核心逻辑。
- 赛道一初赛要求提供 Demo 视频和应用线上链接，因此部署链路不能完全后置，至少要在 MVP 中保留一键生成公网演示地址的接口。

## 当前输入材料

- 比赛要求摘要：`docs/competition-requirements.md`
- 用户 profile：`data/profiles/豆瓣酱`
- 目标 JD：`data/job_descriptions/mechanical-arm-motion-control-algorithm-engineer.md`

## 推荐目录结构

```text
Virtual-Interviewer/
├── apps/
│   └── web/                         # React/Vite 前端
│       ├── src/
│       │   ├── pages/
│       │   ├── components/
│       │   ├── realtime/            # 浏览器录音、字幕、播放、会话事件
│       │   ├── reports/             # 面试报告与能力树视图
│       │   └── api/
│       └── package.json
│
├── services/
│   └── api/                         # FastAPI 后端
│       ├── main.py
│       ├── config.py
│       ├── routers/
│       │   ├── auth.py
│       │   ├── realtime.py          # 前端实时会话入口
│       │   ├── interviews.py
│       │   ├── reports.py
│       │   └── ability_graph.py
│       ├── core/
│       │   ├── interview_state.py   # 面试状态机
│       │   ├── tool_router.py       # Function Calling 工具路由
│       │   ├── scoring.py
│       │   ├── transcript.py
│       │   └── ability_tree.py
│       ├── integrations/
│       │   ├── bailian/
│       │   │   ├── omni_realtime.py # Qwen-Omni-Realtime WebSocket 适配器
│       │   │   ├── function_calling.py
│       │   │   ├── file_search.py
│       │   │   └── web_search.py
│       │   ├── rag/
│       │   │   ├── local_retriever.py
│       │   │   └── profile_loader.py
│       │   └── publish/
│       │       ├── base.py          # 公网访问/站点发布抽象接口
│       │       ├── local.py
│       │       ├── frp.py           # 预留，不急着实现
│       │       ├── cloudflare.py    # 预留
│       │       └── aliyun.py        # 预留：ECS/FC/SAE 等
│       ├── storage/
│       │   ├── db.py
│       │   ├── models.py
│       │   └── repositories.py
│       └── tests/
│
├── data/
│   ├── profiles/                    # 从 interview-assistant 迁移来的简历/profile
│   ├── interviews/                  # 转写、事件、评分
│   └── ability_graphs/              # 每个用户的能力树 JSON
│
├── docs/
│   ├── references.md
│   └── architecture-proposal.md
│
└── scripts/
    ├── dev.ps1
    ├── import_interview_assistant_profile.py
    └── expose_public_url.ps1
```

## 核心模块

### 1. Realtime Gateway

职责：

- 前端只连接自己的后端，不直接暴露 `DASHSCOPE_API_KEY`。
- 后端建立到百炼 Qwen-Omni-Realtime 的 WebSocket。
- 转发音频、图像帧、文本事件、模型输出音频、字幕事件。
- 记录事件流，供转写、评分和复盘使用。

#### Live 音频主链路

后续 live 模式必须坚持 A 路线，由 Qwen-Omni-Realtime 直接理解音频，不在主链路中新增 Whisper/SenseVoice STT：

```text
Browser Microphone
  -> MediaRecorder / AudioWorklet
  -> frontend audio.chunk event
  -> FastAPI /api/interviews/realtime WebSocket
  -> Realtime Gateway
  -> BailianRealtimeAdapter
  -> Qwen-Omni-Realtime WebSocket
  -> assistant.text.delta + assistant.audio.chunk
  -> browser transcript + audio playback
```

前端事件：

```json
{"type": "audio.start", "mime_type": "audio/webm;codecs=opus", "sample_rate": 48000}
{"type": "audio.chunk", "mime_type": "audio/webm;codecs=opus", "data": "<base64>"}
{"type": "audio.stop"}
```

后端事件：

```json
{"type": "assistant.text.delta", "text": "..."}
{"type": "assistant.audio.chunk", "mime_type": "audio/mpeg", "data": "<base64>"}
{"type": "transcript.item", "speaker": "candidate", "text": "..."}
{"type": "realtime.error", "message": "..."}
```

实现原则：

- `MockRealtimeSession` 继续保留，供无 API Key 的本地开发和前端调试使用。
- `BailianRealtimeSession` 新增在 `integrations/bailian/omni_realtime.py`，只负责百炼实时协议适配。
- `RealtimeGateway` 根据 `REALTIME_MODE=mock|bailian` 切换 session 后端。
- 前端先实现 `MediaRecorder`，如果百炼要求 PCM16 或更低延迟，再增加 `AudioWorklet` 转码路径。
- 浏览器麦克风权限和 HTTPS 要在公网演示阶段重点验证；localhost 可直接调试麦克风。

接口草案：

```text
POST /api/realtime/sessions
  创建实时面试会话，返回 session_id 和前端连接地址

WS /api/realtime/sessions/{session_id}/stream
  前端与后端的实时事件通道

POST /api/realtime/sessions/{session_id}/end
  结束会话，触发复盘任务
```

### 2. Interview State Machine

面试阶段：

```text
warmup -> resume_overview -> project_deep_dive -> fundamentals
       -> pressure_followup -> candidate_questions -> summary
```

状态机不直接生成所有回答，而是向 Realtime Gateway 注入会话指令：

- 当前面试阶段。
- 面试官人设。
- 追问策略。
- 候选人目标岗位。
- 本轮需要关注的能力点。

### 3. Tool Router

Function Calling 工具先设计成稳定接口：

```text
retrieve_profile_context(query, user_id)
plan_next_question(stage, transcript, ability_focus)
score_answer(question, answer, rubric)
search_company_context(company, role)
update_ability_tree(user_id, interview_id)
generate_interview_report(user_id, interview_id)
```

注意：百炼文档说明 Qwen3.5-Omni 的联网搜索与 Function Calling 不可同时开启，因此服务层要做策略编排：

- 常规面试：开启 Function Calling。
- 岗位/公司资料准备：单独调用联网搜索或 Responses API。
- 实时会话中如需联网，先由后端工具完成搜索，再把摘要注入会话上下文。

### 4. RAG/Profile

第一版双后端：

- 本地 RAG：复用 `<private-profile-source>` 的 profile、QA bank、简历解析思路。
- 百炼 file_search：后续接入百炼知识库 ID，作为比赛展示亮点。

### 5. Ability Tree

面试后异步更新，不阻塞实时通话。

存储格式先用 JSON：

```json
{
  "user_id": "u_001",
  "skills": [],
  "projects": [],
  "evidence": [],
  "target_skills": [],
  "edges": []
}
```

更新来源：

- 简历与项目材料。
- 面试转写。
- 回答评分。
- 目标岗位 JD。

输出：

- 成长树枝：被新证据支持或评分上升的能力。
- 薄弱树枝：有提及但回答不清的能力。
- 退化树枝：长期未验证或最近表现下降的能力。
- 虚拟树枝：目标岗位需要但当前缺失的能力。

## 公网访问与站点发布预留

### 为什么需要预留

- 比赛演示可能需要让评委从公网访问。
- 如果用浏览器端麦克风/摄像头，HTTPS 基本是必需的。
- 如果部署在中国内地服务器并绑定自定义域名，通常需要 ICP 备案。
- 本地开发阶段可先用内网穿透或临时公网地址，不应耦合进业务代码。

### 抽象接口

```python
class PublicEndpointProvider:
    async def expose(
        self,
        local_port: int,
        protocol: str,
        purpose: str,
    ) -> PublicEndpoint:
        ...

class SitePublicationProvider:
    async def get_status(self) -> SitePublicationStatus:
        ...

    async def describe_next_steps(self) -> list[str]:
        ...
```

候选实现：

- `LocalOnlyProvider`：本地开发，返回 `http://localhost:5173`。
- `FrpProvider`：连接自建公网 ECS 上的 frps，适合演示。
- `CloudflareTunnelProvider`：预留海外/临时演示。
- `AliyunProvider`：预留正式部署，支持 ECS、SAE、函数计算、自定义域名状态查询。

### 部署路线

```text
阶段 1：本地开发
  Vite + FastAPI + SQLite + 本地 profile/RAG

阶段 2：公网演示
  本地服务 + frp/ngrok/Cloudflare Tunnel
  或轻量 ECS 直接部署

阶段 3：正式参赛部署
  前端静态站点 + 后端 API 服务
  可选 ECS/SAE/函数计算
  域名、HTTPS、备案状态独立管理

阶段 4：稳定上线
  数据库托管、对象存储、日志监控、权限系统、限流和成本监控
```

## 需要用户确认的问题

1. 第一版前端是否确定为 Web App？
2. Realtime 接入第一版是否优先 WebSocket，WebRTC 仅预留？
3. 公网演示是否接受先用内网穿透，正式域名/备案作为后续任务？
