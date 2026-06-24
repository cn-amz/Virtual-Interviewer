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

    async def connect(self) -> None:
        """Validate configuration and establish live session.

        Raises RuntimeError if config is incomplete.
        Raises NotImplementedError until the live protocol mapping is wired.
        """
        self.validate_ready()
        raise NotImplementedError(
            "Bailian live audio protocol mapping is not wired yet. "
            "Qwen-Omni-Realtime event mapping requires official protocol specification."
        )

    async def send_audio_start(self, mime_type: str, sample_rate: int | None) -> None:
        raise NotImplementedError("Live protocol not wired.")

    async def send_audio_chunk(self, data_base64: str, mime_type: str) -> None:
        raise NotImplementedError("Live protocol not wired.")

    async def send_audio_stop(self) -> None:
        raise NotImplementedError("Live protocol not wired.")

    async def close(self) -> None:
        pass
