from dataclasses import dataclass


@dataclass(frozen=True)
class BailianRealtimeConfig:
    api_key: str | None
    model: str
    url: str


class BailianRealtimeAdapter:
    def __init__(self, config: BailianRealtimeConfig):
        self.config = config

    def validate_ready(self) -> None:
        if not self.config.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for Bailian live realtime mode.")
        if not self.config.model:
            raise RuntimeError("Bailian realtime model is required.")
        if not self.config.url.startswith("wss://"):
            raise RuntimeError("Bailian realtime URL must start with wss://.")
