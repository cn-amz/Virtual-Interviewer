import { describe, expect, it } from "vitest";
import { appendRealtimeEvent, type RealtimeEvent } from "./useInterviewSession";

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
