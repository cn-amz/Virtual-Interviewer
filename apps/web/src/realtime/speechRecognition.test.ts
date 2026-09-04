import { afterEach, describe, expect, it, vi } from "vitest";
import { createSpeechRecognition } from "./speechRecognition";

class FakeRecognition {
  continuous = false;
  interimResults = false;
  lang = "";
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0?: { transcript?: string } }> }) => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error?: string }) => void) | null = null;
  start = vi.fn();
  stop = vi.fn(() => this.onend?.());
}

afterEach(() => vi.unstubAllGlobals());

describe("createSpeechRecognition", () => {
  it("emits partial text and one final transcript when microphone capture stops", () => {
    let recognition: FakeRecognition | undefined;
    vi.stubGlobal("window", {
      webkitSpeechRecognition: class extends FakeRecognition {
        constructor() {
          super();
          recognition = this;
        }
      },
    });
    const onPartial = vi.fn();
    const onFinal = vi.fn();
    const capture = createSpeechRecognition({ onPartial, onFinal, onError: vi.fn() });

    capture?.start();
    recognition?.onresult?.({
      resultIndex: 0,
      results: [{ isFinal: false, 0: { transcript: "我负责" } }],
    });
    recognition?.onresult?.({
      resultIndex: 0,
      results: [{ isFinal: true, 0: { transcript: "控制器开发。" } }],
    });
    capture?.stop();

    expect(onPartial).toHaveBeenLastCalledWith("控制器开发。");
    expect(onFinal).toHaveBeenCalledWith("控制器开发。");
  });
});
