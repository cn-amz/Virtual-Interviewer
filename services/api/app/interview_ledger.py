from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    """Keep event metadata while excluding raw audio from the durable ledger."""
    result = dict(event)
    if result.get("type") in {"audio.chunk", "assistant.audio.chunk"} and "data" in result:
        encoded = str(result.pop("data") or "")
        try:
            result["bytes"] = len(base64.b64decode(encoded, validate=True))
        except (binascii.Error, ValueError):
            result["bytes"] = 0
        result["audio_persisted"] = False
    return result


class InterviewLedger:
    def __init__(
        self,
        interview_id: str,
        user_id: str,
        profile_id: str,
        jd_id: str,
        resume_name: str = "",
        *,
        authoritative_asr: str = "provider_asr",
    ):
        self.interview_id = interview_id
        self.user_id = user_id
        self.profile_id = profile_id
        self.jd_id = jd_id
        self.resume_name = resume_name
        self.authoritative_asr = authoritative_asr
        self.started_at = _now()
        self.events: list[dict[str, Any]] = []
        self.transcript: list[dict[str, str]] = []
        self.audio_metrics = {
            "input_chunks": 0,
            "input_bytes": 0,
            "output_chunks": 0,
            "output_bytes": 0,
        }
        self._assistant_buffer = ""
        self._assistant_turn_id = ""
        self._assistant_source = ""

    def record(self, direction: str, event: dict[str, Any]) -> None:
        if event.get("type") in {"audio.chunk", "assistant.audio.chunk"}:
            sanitized = sanitize_event(event)
            prefix = "input" if event.get("type") == "audio.chunk" else "output"
            self.audio_metrics[f"{prefix}_chunks"] += 1
            self.audio_metrics[f"{prefix}_bytes"] += int(sanitized.get("bytes", 0))
            return
        self.events.append(
            {
                "at": _now(),
                "direction": direction,
                "event": sanitize_event(event),
            }
        )
        self._record_transcript(direction, event)

    def _record_transcript(self, direction: str, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if event_type == "transcript.item" and event.get("text"):
            source = str(event.get("source", ""))
            if direction == "client":
                source = "browser_asr"
            if source in {"provider_asr", "browser_asr"} and source != self.authoritative_asr:
                return
            if event.get("speaker") == "candidate":
                self._flush_assistant()
            self._upsert_transcript(
                self._transcript_row(
                    str(event.get("speaker", "candidate")),
                    str(event["text"]),
                    str(event.get("turn_id", "")),
                    source,
                )
            )
        elif event_type == "assistant.text.delta":
            turn_id = str(event.get("turn_id", ""))
            source = str(event.get("source", ""))
            if self._assistant_buffer and (
                (turn_id and turn_id != self._assistant_turn_id)
                or (source and source != self._assistant_source)
            ):
                self._flush_assistant()
            self._assistant_turn_id = turn_id or self._assistant_turn_id
            self._assistant_source = source or self._assistant_source
            self._assistant_buffer += str(event.get("text", ""))
        elif event_type == "bailian.event" and event.get("event") == "response.done":
            self._flush_assistant()

    def _flush_assistant(self) -> None:
        if self._assistant_buffer.strip():
            self._upsert_transcript(
                self._transcript_row(
                    "assistant",
                    self._assistant_buffer.strip(),
                    self._assistant_turn_id,
                    self._assistant_source,
                )
            )
        self._assistant_buffer = ""
        self._assistant_turn_id = ""
        self._assistant_source = ""

    @staticmethod
    def _transcript_row(speaker: str, text: str, turn_id: str, source: str) -> dict[str, str]:
        row = {"speaker": speaker, "text": text}
        if turn_id:
            row["turn_id"] = turn_id
        if source:
            row["source"] = source
        return row

    def _upsert_transcript(self, row: dict[str, str]) -> None:
        turn_id = row.get("turn_id")
        if turn_id:
            for index, existing in enumerate(self.transcript):
                if existing.get("speaker") == row["speaker"] and existing.get("turn_id") == turn_id:
                    self.transcript[index] = row
                    return
        self.transcript.append(row)

    def payload(self, status: str = "completed", close_reason: str | None = None) -> dict[str, Any]:
        self._flush_assistant()
        return {
            "interview_id": self.interview_id,
            "user_id": self.user_id,
            "profile_id": self.profile_id,
            "jd_id": self.jd_id,
            "resume_name": self.resume_name,
            "status": status,
            "close_reason": close_reason,
            "started_at": self.started_at,
            "ended_at": _now(),
            "events": self.events,
            "transcript": self.transcript,
            "audio_metrics": dict(self.audio_metrics),
        }
