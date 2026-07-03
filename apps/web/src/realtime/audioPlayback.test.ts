import { describe, expect, it } from "vitest";
import { decodePcm16Base64 } from "./audioPlayback";

describe("decodePcm16Base64", () => {
  it("decodes little-endian PCM16 samples into float audio samples", () => {
    const bytes = new Uint8Array([0x00, 0x00, 0xff, 0x7f, 0x00, 0x80]);
    const base64 = btoa(String.fromCharCode(...bytes));

    const samples = decodePcm16Base64(base64);

    expect(Array.from(samples)).toEqual([0, 32767 / 32768, -1]);
  });
});
