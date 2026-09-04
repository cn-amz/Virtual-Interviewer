import { afterEach, describe, expect, it } from "vitest";
import { createPcmAudioPlayer, decodePcm16Base64 } from "./audioPlayback";

const originalWindow = globalThis.window;

afterEach(() => {
  Object.defineProperty(globalThis, "window", { value: originalWindow, configurable: true });
});

describe("decodePcm16Base64", () => {
  it("decodes little-endian PCM16 samples into float audio samples", () => {
    const bytes = new Uint8Array([0x00, 0x00, 0xff, 0x7f, 0x00, 0x80]);
    const base64 = btoa(String.fromCharCode(...bytes));

    const samples = decodePcm16Base64(base64);

    expect(Array.from(samples)).toEqual([0, 32767 / 32768, -1]);
  });
});

describe("createPcmAudioPlayer", () => {
  it("reports active playback until every queued source ends", async () => {
    const sources: Array<{ onended: (() => void) | null }> = [];
    class FakeAudioContext {
      currentTime = 0;
      state = "running";
      destination = {};
      createBuffer(_channels: number, length: number, sampleRate: number) {
        return {
          duration: length / sampleRate,
          getChannelData: () => new Float32Array(length),
        };
      }
      createBufferSource() {
        const source = {
          buffer: null,
          onended: null as (() => void) | null,
          connect: () => undefined,
          start: () => undefined,
        };
        sources.push(source);
        return source;
      }
      resume() { return Promise.resolve(); }
      close() { this.state = "closed"; return Promise.resolve(); }
    }
    Object.defineProperty(globalThis, "window", {
      value: { AudioContext: FakeAudioContext },
      configurable: true,
    });
    const states: boolean[] = [];
    const player = createPcmAudioPlayer((active) => states.push(active));
    const chunk = btoa(String.fromCharCode(0, 0));

    await player.playChunk(chunk, 24000);
    await player.playChunk(chunk, 24000);
    expect(states).toEqual([true]);

    sources[0].onended?.();
    expect(states).toEqual([true]);
    sources[1].onended?.();
    expect(states).toEqual([true, false]);
  });
});
