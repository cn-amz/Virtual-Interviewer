import { describe, expect, it } from "vitest";
import {
  appendRealtimeEvent,
  buildRealtimeUrl,
  deriveMessages,
  isNearBottom,
  isProviderReady,
  reduceSessionState,
  shouldUseBrowserAsr,
  shouldUploadMicrophone,
  type RealtimeEvent,
} from "./useInterviewSession";

describe("provider transcription policy", () => {
  it("uses browser ASR only for MiniCPM", () => {
    expect(shouldUseBrowserAsr("bailian")).toBe(false);
    expect(shouldUseBrowserAsr("minicpm")).toBe(true);
  });
});

describe("provider readiness policy", () => {
  it("allows a new connection only when the provider is idle", () => {
    expect(isProviderReady("idle")).toBe(true);
    expect(isProviderReady("loading")).toBe(false);
    expect(isProviderReady("busy")).toBe(false);
    expect(isProviderReady("offline")).toBe(false);
    expect(isProviderReady(undefined)).toBe(false);
  });
});

describe("playback upload policy", () => {
  it("keeps full duplex as the default behavior and gates only the optional mode", () => {
    expect(shouldUploadMicrophone("full_duplex", true)).toBe(true);
    expect(shouldUploadMicrophone("playback_gate", false)).toBe(true);
    expect(shouldUploadMicrophone("playback_gate", true)).toBe(false);
  });
});

describe("reduceSessionState", () => {
  it("waits for durable completion before becoming persisted", () => {
    expect(reduceSessionState("ready", { type: "finish" })).toBe("ending");
    expect(reduceSessionState("ending", { type: "persisted", status: "completed" })).toBe(
      "persisted"
    );
  });

  it("returns cancelled sessions to idle and exposes connection errors", () => {
    expect(reduceSessionState("ready", { type: "cancel" })).toBe("ending");
    expect(reduceSessionState("ending", { type: "persisted", status: "cancelled" })).toBe(
      "idle"
    );
    expect(reduceSessionState("connecting", { type: "error" })).toBe("error");
  });
});

describe("appendRealtimeEvent", () => {
  it("updates the latest partial transcript instead of appending repeated cards", () => {
    const events: RealtimeEvent[] = [
      { type: "session.ready" },
      { type: "transcript.partial", speaker: "candidate", text: "你好" },
    ];

    const next = appendRealtimeEvent(events, {
      type: "transcript.partial",
      speaker: "candidate",
      text: "你好，我是",
    });

    expect(next).toEqual([
      { type: "session.ready" },
      { type: "transcript.partial", speaker: "candidate", text: "你好，我是" },
    ]);
  });

  it("replaces the latest partial transcript with the final candidate transcript", () => {
    const next = appendRealtimeEvent(
      [{ type: "transcript.partial", speaker: "candidate", text: "项目是" }],
      { type: "transcript.item", speaker: "candidate", text: "项目是机械臂控制。" }
    );

    expect(next).toEqual([
      { type: "transcript.item", speaker: "candidate", text: "项目是机械臂控制。" },
    ]);
  });

  it("replaces a candidate partial even when an audio event arrives before the final transcript", () => {
    const next = appendRealtimeEvent(
      [
        { type: "transcript.partial", speaker: "candidate", text: "我负责" },
        { type: "assistant.audio.chunk", data: "AAAA", sample_rate: 24000 },
      ],
      { type: "transcript.item", speaker: "candidate", text: "我负责控制器开发。" }
    );

    expect(next).toEqual([
      { type: "transcript.item", speaker: "candidate", text: "我负责控制器开发。" },
      { type: "assistant.audio.chunk", data: "AAAA", sample_rate: 24000 },
    ]);
  });

  it("updates the latest assistant audio chunk instead of appending repeated cards", () => {
    const next = appendRealtimeEvent(
      [{ type: "assistant.audio.chunk", data: "AAAA", sample_rate: 24000 }],
      { type: "assistant.audio.chunk", data: "BBBB", sample_rate: 24000 }
    );

    expect(next).toEqual([
      { type: "assistant.audio.chunk", data: "BBBB", sample_rate: 24000 },
    ]);
  });

  it("merges assistant text deltas across audio chunks into one visible reply", () => {
    const events = appendRealtimeEvent(
      [
        { type: "transcript.item", speaker: "candidate", text: "我做过机械臂控制。" },
        { type: "assistant.text.delta", text: "请说明" },
        { type: "assistant.audio.chunk", data: "AAAA", sample_rate: 24000 },
      ],
      { type: "assistant.text.delta", text: "你如何验证稳定性。" }
    );

    expect(events).toEqual([
      { type: "transcript.item", speaker: "candidate", text: "我做过机械臂控制。" },
      { type: "assistant.text.delta", text: "请说明你如何验证稳定性。" },
      { type: "assistant.audio.chunk", data: "AAAA", sample_rate: 24000 },
    ]);
  });
});

describe("deriveMessages", () => {
  it("updates interleaved events by turn identity without mixing bubbles", () => {
    expect(
      deriveMessages([
        { type: "assistant.text.delta", turn_id: "a1", text: "第一个问题" },
        { type: "transcript.partial", speaker: "candidate", turn_id: "u1", text: "回答中" },
        { type: "assistant.text.delta", turn_id: "a1", text: "。" },
        {
          type: "transcript.item",
          speaker: "candidate",
          turn_id: "u1",
          text: "完整回答",
          is_final: true,
        },
      ])
    ).toEqual([
      { id: "a1", role: "assistant", text: "第一个问题。", isFinal: false },
      { id: "u1", role: "user", text: "完整回答", isFinal: true },
    ]);
  });

  it("merges candidate partials into a single user message", () => {
    const messages = deriveMessages([
      { type: "transcript.partial", speaker: "candidate", text: "你好" },
      { type: "transcript.partial", speaker: "candidate", text: "你好，我是" },
      { type: "transcript.item", speaker: "candidate", text: "你好，我是豆瓣酱。" },
    ]);

    expect(messages).toEqual([
      { id: "legacy-user-1", role: "user", text: "你好，我是豆瓣酱。", isFinal: true },
    ]);
  });

  it("merges assistant text deltas into one assistant message per response", () => {
    const messages = deriveMessages([
      { type: "assistant.text.delta", text: "请说明" },
      { type: "assistant.audio.chunk", data: "AAAA", sample_rate: 24000 },
      { type: "assistant.text.delta", text: "你如何验证稳定性。" },
    ]);

    expect(messages).toEqual([
      {
        id: "legacy-assistant-1",
        role: "assistant",
        text: "请说明你如何验证稳定性。",
        isFinal: false,
      },
    ]);
  });

  it("starts a new assistant message after response.done", () => {
    const messages = deriveMessages([
      { type: "assistant.text.delta", text: "第一句回复" },
      { type: "bailian.event", event: "response.done" },
      { type: "assistant.text.delta", text: "第二句回复" },
    ]);

    expect(messages).toEqual([
      { id: "legacy-assistant-1", role: "assistant", text: "第一句回复", isFinal: true },
      { id: "legacy-assistant-2", role: "assistant", text: "第二句回复", isFinal: false },
    ]);
  });

  it("starts a new assistant message after a MiniCPM turn completes", () => {
    const messages = deriveMessages([
      { type: "assistant.text.delta", text: "第一句回复" },
      { type: "assistant.turn.completed", mode: "minicpm" },
      { type: "assistant.text.delta", text: "第二句回复" },
    ]);

    expect(messages).toEqual([
      { id: "legacy-assistant-1", role: "assistant", text: "第一句回复", isFinal: true },
      { id: "legacy-assistant-2", role: "assistant", text: "第二句回复", isFinal: false },
    ]);
  });

  it("ignores status and debug events", () => {
    const messages = deriveMessages([
      { type: "session.ready", mode: "bailian" },
      { type: "assistant.audio.chunk", data: "AAAA", sample_rate: 24000 },
      { type: "client.pending", message: "等待回复" },
      { type: "bailian.event", event: "input_audio_buffer.speech_started" },
      { type: "bailian.event", event: "response.done" },
      { type: "audio.stopped", mode: "bailian" },
    ]);

    expect(messages).toEqual([]);
  });

  it("separates user and assistant turns", () => {
    const messages = deriveMessages([
      { type: "transcript.item", speaker: "candidate", text: "我做过机械臂控制。" },
      { type: "assistant.text.delta", text: "你如何验证稳定性？" },
      { type: "transcript.item", speaker: "candidate", text: "通过仿真。" },
    ]);

    expect(messages).toEqual([
      { id: "legacy-user-1", role: "user", text: "我做过机械臂控制。", isFinal: true },
      {
        id: "legacy-assistant-1",
        role: "assistant",
        text: "你如何验证稳定性？",
        isFinal: false,
      },
      { id: "legacy-user-2", role: "user", text: "通过仿真。", isFinal: true },
    ]);
  });
});

describe("isNearBottom", () => {
  it("uses an 80px follow threshold", () => {
    expect(isNearBottom(900, 500, 1450)).toBe(true);
    expect(isNearBottom(300, 500, 1450)).toBe(false);
  });
});

describe("buildRealtimeUrl", () => {
  it("passes the selected provider, profile, resume, and job description to the session", () => {
    expect(
      buildRealtimeUrl({
        provider: "minicpm",
        audioMode: "full_duplex",
        profileId: "候选人甲",
        resumeName: "算法岗位简历.docx",
        jdId: "运动规划岗",
      })
    ).toBe(
      "ws://localhost:8000/api/interviews/realtime?provider=minicpm&profile_id=%E5%80%99%E9%80%89%E4%BA%BA%E7%94%B2&resume_name=%E7%AE%97%E6%B3%95%E5%B2%97%E4%BD%8D%E7%AE%80%E5%8E%86.docx&jd_id=%E8%BF%90%E5%8A%A8%E8%A7%84%E5%88%92%E5%B2%97"
    );
  });
});
