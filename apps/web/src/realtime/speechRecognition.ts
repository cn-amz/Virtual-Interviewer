export type SpeechRecognitionCallbacks = {
  onPartial: (text: string) => void;
  onFinal: (text: string) => void;
  onError: (message: string) => void;
};

type SpeechResult = {
  isFinal: boolean;
  0?: { transcript?: string };
};

type SpeechResultEvent = {
  resultIndex: number;
  results: ArrayLike<SpeechResult>;
};

type BrowserSpeechRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  start: () => void;
  stop: () => void;
};

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

export type SpeechRecognitionCapture = {
  start: () => void;
  stop: () => void;
};

export function createSpeechRecognition(
  callbacks: SpeechRecognitionCallbacks
): SpeechRecognitionCapture | undefined {
  const browserWindow = window as typeof window & {
    SpeechRecognition?: BrowserSpeechRecognitionConstructor;
    webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
  };
  const Recognition = browserWindow.SpeechRecognition ?? browserWindow.webkitSpeechRecognition;
  if (!Recognition) return undefined;

  const recognition = new Recognition();
  const finalSegments: string[] = [];
  let interim = "";
  let finished = false;

  function currentText(): string {
    return [...finalSegments, interim].join("").trim();
  }

  function finish(): void {
    if (finished) return;
    finished = true;
    const text = currentText();
    if (text) callbacks.onFinal(text);
  }

  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "zh-CN";
  recognition.onresult = (event) => {
    interim = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      const text = result[0]?.transcript?.trim() ?? "";
      if (result.isFinal) finalSegments.push(text);
      else interim += text;
    }
    callbacks.onPartial(currentText());
  };
  recognition.onerror = (event) => {
    if (event.error !== "aborted" && event.error !== "no-speech") {
      const message = event.error === "not-allowed"
        ? "浏览器拒绝了语音识别权限。请在站点权限中允许麦克风和语音识别；Codex 内嵌浏览器可能不支持该能力，请用 Edge 或 Chrome 正常窗口打开页面。"
        : `浏览器语音识别失败：${event.error ?? "未知错误"}。`;
      callbacks.onError(message);
    }
  };
  recognition.onend = finish;

  return {
    start: () => recognition.start(),
    stop: () => recognition.stop(),
  };
}
