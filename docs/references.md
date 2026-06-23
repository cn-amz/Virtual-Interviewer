# 虚拟面试官参考资料与设计锚点

更新时间：2026-06-23

## 比赛方向

- 赛题强调 LLM、RAG、Function Calling、零代码/低代码与智能体自主规划执行能力。
- 项目定位建议：实时通话型虚拟面试官 Agent，围绕“面试前准备、实时面试、工具增强、面后复盘”形成完整闭环。
- 已保存结构化比赛摘要：`docs/competition-requirements.md`。
- 已导入用户 profile：`data/profiles/豆瓣酱`。
- 已准备占位 JD：`data/job_descriptions/mechanical-arm-motion-control-algorithm-engineer.md`。

## 阿里云百炼能力

### Qwen-Omni-Realtime

- 官方定位：实时音视频聊天模型，可理解流式音频与图像输入，并实时输出文本与音频。
- 接入方式：支持 WebSocket 与 WebRTC。
- 设计取舍：
  - WebSocket：适合服务端集成和快速 PoC。
  - WebRTC：适合浏览器端低延迟语音场景，音频经 UDP 传输，并内置回声消除和降噪；但官方文档标注 WebRTC 功能目前为白名单开放。
- 候选模型：`qwen3.5-omni-plus-realtime`、`qwen3.5-omni-flash-realtime`。
- 参考链接：https://help.aliyun.com/zh/model-studio/realtime

### 全模态与实时工具能力

- Qwen3.5-Omni 支持 Function Calling；实时系列也在 Function Calling 支持模型列表中。
- Qwen3.5-Omni 支持联网搜索，但官方说明中联网搜索与 Function Calling 不可同时开启，需要在单轮策略里二选一或由外部服务层编排。
- 参考链接：https://help.aliyun.com/zh/model-studio/omni/

### Function Calling

- 百炼 Function Calling 可用于让模型选择并调用外部工具。
- 适合本项目的工具：
  - `retrieve_profile_context`：检索简历、项目经历、JD 与准备材料。
  - `plan_next_question`：根据面试阶段与候选人回答生成下一问。
  - `score_answer`：按结构、技术深度、可信度、表达清晰度评分。
  - `search_company_context`：联网查询公司/岗位/技术栈背景。
  - `generate_report`：生成面试复盘报告与训练计划。
- 参考链接：https://help.aliyun.com/zh/model-studio/qwen-function-calling

### 知识检索与联网搜索

- `file_search`：Responses API 的知识检索工具，可通过 `vector_store_ids` 指向百炼知识库。
- `web_search`：可用于实时联网搜索；对比赛演示可作为“岗位/公司背景增强”的亮点。
- 参考链接：
  - https://help.aliyun.com/zh/model-studio/file-search
  - https://help.aliyun.com/zh/model-studio/web-search

## MiniCPM-V / MiniCPM-o 参考点

- MiniCPM-V 专注高效视觉语言理解，MiniCPM-o 扩展到实时端到端全模态交互。
- MiniCPM-o 的关键参考点：输出流（语音和文本）与实时输入流（视频和音频）互不阻塞，可实现“边看、边听、边说”与主动提醒。
- 在本项目中建议作为设计思想与对照说明，而不是主链路依赖；主链路应优先使用阿里云百炼 API 以匹配比赛要求。
- 参考链接：https://github.com/OpenBMB/MiniCPM-V/blob/main/README_zh.md

## 从 `<private-profile-source>` 可复用的资产

- 可复用：
  - 简历解析与 profile 概念。
  - 本地 QA/RAG 结构与问答库格式。
  - 语义纠错、术语热词思路。
  - 流式输出与中断处理经验。
- 需要重构：
  - 从“面试辅助回答悬浮窗”改为“虚拟面试官主动提问与评分”。
  - 从 Whisper/本地音频管线转向百炼 Qwen-Omni-Realtime 主链路。
  - 从单向辅助输出转向双向实时会话状态机。

## A 与 B 的核心区别

- A：Qwen-Omni-Realtime 原生实时模型作为主链路。更符合“全双工实时对话”和“必须使用阿里 API”的比赛叙事。
- B：ASR + LLM + TTS 模块化流水线。可以做低延迟、可打断、边听边打断播报，但本质上是服务层编排出来的轮次系统，不是模型原生全双工。

## 能力知识图谱与能力树

- 建议定位：面试后复盘报告与长期成长画像，不放入实时通话主链路。
- 每个用户维护一棵个人“总能力树”，由简历、项目材料、历史面试转写、评分记录共同生长。
- 每次面试后异步生成能力知识图谱更新：
  - 强证据节点：回答清晰、有项目证据支撑的能力点。
  - 弱证据节点：简历写了但面试中解释不足的能力点。
  - 退化节点：长期未覆盖、最近回答质量下降或证据过旧的能力点。
  - 虚拟树枝：目标岗位需要但当前用户缺失或薄弱的能力点，作为后续训练路线。
- MVP 节点类型：
  - `User`：用户画像。
  - `Skill`：能力点，例如 WebSocket、RAG、机器人控制、系统设计。
  - `Project`：项目经历。
  - `Evidence`：简历片段、面试回答片段、代码/文档证据。
  - `TargetSkill`：目标岗位要求中的待提升能力。
- MVP 边类型：
  - `Project uses Skill`
  - `Evidence supports Skill`
  - `Skill related_to Skill`
  - `TargetSkill requires Skill`
  - `Skill has_gap TargetSkill`
- 轻量实现建议：先用 JSON 存储图谱，不急于引入图数据库；展示层可用 React Flow、Cytoscape.js 或 D3。
