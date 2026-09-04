from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


INDUSTRY_REFERENCE_SOURCES = [
    {
        "title": "海康机器人：运动控制算法工程师",
        "url": "https://talent.hikvision.com/society/position?postId=34D120423CCEE750C1A0E1E5ECC540F8",
        "note": "控制端架构、路径规划、仿真测试、PLCopen、PID、自适应控制和 EtherCAT/CANopen。",
    },
    {
        "title": "上海人工智能实验室：机器人运控算法工程师",
        "url": "https://www.shlab.org.cn/joinus/detail/7649605753204279590?mode=social",
        "note": "异构机器人规划控制、真机实验、MPC/PID/RL、C/C++/Python 和算法落地。",
    },
    {
        "title": "中控信息：运动控制算法工程师（机器人-机械臂方向）",
        "url": "https://www.zhaopin.com/jobdetail/CC121142370J40751742506.htm",
        "note": "六轴/七轴机械臂、MoveIt2、碰撞检测、运动学求解、视觉控制和真机验证。",
    },
    {
        "title": "黑格智造：运控算法工程师",
        "url": "https://career.hebut.edu.cn/home/correcruit/content/id/78856.html",
        "note": "FOC、电机控制、振动抑制、参数自整定、MATLAB/Simulink 和 ARM/DSP 部署。",
    },
]


def _has(text: str, *keywords: str) -> bool:
    return any(keyword.lower() in text.lower() for keyword in keywords)


def _role_direction(title: str, content: str) -> tuple[str, list[str]]:
    text = f"{title}\n{content}"
    if _has(text, "FOC", "PMSM", "BLDC", "电机控制", "伺服驱动", "ARM/DSP"):
        return "电机与伺服控制", ["FOC/PID 与电机控制", "振动抑制与参数整定", "实时总线与嵌入式部署", "示波器/时序问题定位"]
    if _has(text, "机械臂", "MoveIt", "手眼", "抓取", "逆运动学", "视觉伺服") and not _has(text, "人形", "全身", "步态", "WBC"):
        return "机械臂规划、控制与操作", ["运动学/逆运动学与 MoveIt", "轨迹规划、平滑和碰撞检测", "视觉/手眼标定闭环", "仿真到真机验证"]
    if _has(text, "人形", "全身", "异构", "步态", "WBC", "强化学习", "RL"):
        return "人形与异构机器人规划控制", ["全身/多约束运动规划", "MPC/PID/RL 控制器", "真机实验与稳定性指标", "C++/Python 工程落地"]
    if _has(text, "底盘", "移动机器人", "导航", "避障", "路径跟踪"):
        return "移动机器人导航与控制", ["运动学/动力学建模", "轨迹跟踪与避障", "定位导航与控制闭环", "现场异常和实时性分析"]
    if _has(text, "视觉", "感知", "三维", "目标检测", "点云"):
        return "机器人感知与操作闭环", ["感知结果到动作的接口", "标定与坐标系", "抓取/操作任务成功率", "异常恢复与工程验证"]
    return "机器人运动规划与控制工程", ["控制理论与建模", "规划/控制接口", "软件工程与调试", "仿真、真机和指标验证"]


def deterministic_job_analysis(jd_id: str, title: str, content: str) -> dict[str, Any]:
    direction, focus_points = _role_direction(title, content)
    return {
        "jd_id": jd_id,
        "title": title,
        "role_family": "机器人算法与运动控制",
        "role_direction": direction,
        "focus_points": focus_points,
        "question_strategy": [
            "先让候选人用一个项目说明个人职责，再逐层追问算法、接口、指标和失败复盘。",
            "优先验证 JD 中明确出现的工具、控制方法和真实部署经验，不把关键词命中当成能力证据。",
            "候选人回答空泛时追问可测量指标、边界条件、工程取舍和本人代码范围。",
        ],
        "initial_prompt": (
            f"你正在面试“{title}”，岗位实际方向是“{direction}”。"
            "你是一名真实技术面试官，不是知识问答助手。优先围绕以下关注点提问："
            f"{'、'.join(focus_points)}。每轮只问一个问题，必须结合候选人简历和 JD 证据，"
            "先验证候选人本人做了什么，再追问技术原因、指标、边界和失败复盘。"
        ),
        "source_keywords": _source_keywords(title, content),
        "research_sources": deepcopy(INDUSTRY_REFERENCE_SOURCES),
        "analysis_mode": "deterministic_fallback",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _source_keywords(title: str, content: str) -> list[str]:
    candidates = (
        "ROS2", "MoveIt", "PID", "MPC", "RL", "FOC", "EtherCAT", "CANopen",
        "视觉伺服", "手眼标定", "轨迹规划", "动力学", "逆运动学", "真机验证",
    )
    text = f"{title}\n{content}"
    return [keyword for keyword in candidates if keyword.lower() in text.lower()]


def _prompt(jd_id: str, title: str, content: str) -> str:
    sources = "\n".join(
        f"- {item['title']}：{item['note']}（{item['url']}）"
        for item in INDUSTRY_REFERENCE_SOURCES
    )
    return (
        "你是技术招聘方向分析器，只输出 JSON，不要 Markdown。\n"
        "请根据岗位 JD 正文，并参考公开岗位样本，识别这个岗位真正偏向的技术方向。"
        "岗位名称可能与实际方向不一致，不能仅依据岗位名称判断。不要编造 JD 未出现的硬性要求，"
        "可以把行业样本中的内容标记为建议验证项。输出字段："
        "role_family、role_direction、focus_points（4-8 个面试关注点数组）、"
        "question_strategy（3-5 条追问策略数组）、initial_prompt（给真实技术面试官的中文身份和行为约束，"
        "不能写成知识助手）、source_keywords（JD 中出现的关键词数组）。\n"
        f"jd_id：{jd_id}\n岗位标题：{title}\n岗位正文：{content}\n"
        f"公开行业样本：\n{sources}"
    )


def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Job analysis must be a JSON object")
    return value


async def analyze_job_description(jd_id: str, title: str, content: str, text_client: Any | None) -> dict[str, Any]:
    fallback = deterministic_job_analysis(jd_id, title, content)
    if text_client is None:
        return fallback
    try:
        data = _parse_json(await text_client.analyze_job_description(_prompt(jd_id, title, content)))
        required = ("role_family", "role_direction", "focus_points", "question_strategy", "initial_prompt")
        if any(not str(data.get(key, "")).strip() for key in required):
            raise ValueError("Job analysis omitted required fields")
        if not isinstance(data["focus_points"], list) or not isinstance(data["question_strategy"], list):
            raise ValueError("Job analysis list fields are invalid")
        return {
            **fallback,
            **{key: data[key] for key in required},
            "source_keywords": data.get("source_keywords", fallback["source_keywords"]),
            "analysis_mode": "bailian_text",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        fallback["analysis_error"] = type(exc).__name__
        return fallback
