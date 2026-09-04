import base64
import json

from app.interview_ledger import InterviewLedger


def test_ledger_ignores_non_authoritative_browser_asr_for_bailian():
    ledger = InterviewLedger(
        "iv_test",
        "demo",
        "demo",
        "jd",
        authoritative_asr="provider_asr",
    )

    ledger.record(
        "client",
        {
            "type": "transcript.item",
            "speaker": "candidate",
            "text": "混入内容",
            "turn_id": "b1",
            "source": "browser_asr",
        },
    )
    ledger.record(
        "provider",
        {
            "type": "transcript.item",
            "speaker": "candidate",
            "text": "真实回答",
            "turn_id": "p1",
            "source": "provider_asr",
        },
    )

    assert ledger.payload()["transcript"] == [
        {
            "speaker": "candidate",
            "text": "真实回答",
            "turn_id": "p1",
            "source": "provider_asr",
        }
    ]


def test_ledger_rejects_legacy_untagged_client_transcript_for_bailian():
    ledger = InterviewLedger(
        "iv_test",
        "demo",
        "demo",
        "jd",
        authoritative_asr="provider_asr",
    )

    ledger.record(
        "client",
        {
            "type": "transcript.item",
            "speaker": "candidate",
            "text": "浏览器旧事件",
            "turn_id": "legacy-browser-1",
        },
    )

    assert ledger.payload()["transcript"] == []


def test_ledger_does_not_trust_client_claiming_to_be_provider_asr():
    ledger = InterviewLedger(
        "iv_test",
        "demo",
        "demo",
        "jd",
        authoritative_asr="provider_asr",
    )

    ledger.record(
        "client",
        {
            "type": "transcript.item",
            "speaker": "candidate",
            "text": "伪造来源",
            "turn_id": "spoofed-provider-1",
            "source": "provider_asr",
        },
    )

    assert ledger.payload()["transcript"] == []


def test_ledger_infers_legacy_minicpm_client_transcript_as_browser_asr():
    ledger = InterviewLedger(
        "iv_test",
        "demo",
        "demo",
        "jd",
        authoritative_asr="browser_asr",
    )

    ledger.record(
        "client",
        {
            "type": "transcript.item",
            "speaker": "candidate",
            "text": "本地浏览器转写",
            "turn_id": "legacy-browser-1",
        },
    )

    assert ledger.payload()["transcript"] == [
        {
            "speaker": "candidate",
            "text": "本地浏览器转写",
            "turn_id": "legacy-browser-1",
            "source": "browser_asr",
        }
    ]


def test_ledger_keeps_application_text_and_groups_assistant_deltas_by_turn():
    ledger = InterviewLedger(
        "iv_test",
        "demo",
        "demo",
        "jd",
        authoritative_asr="provider_asr",
    )

    ledger.record(
        "server",
        {
            "type": "transcript.item",
            "speaker": "candidate",
            "text": "手动输入",
            "turn_id": "local-candidate-1",
            "source": "application",
        },
    )
    ledger.record(
        "provider",
        {
            "type": "assistant.text.delta",
            "text": "第一段",
            "turn_id": "resp_1",
            "source": "provider",
        },
    )
    ledger.record(
        "provider",
        {
            "type": "assistant.text.delta",
            "text": "第二段",
            "turn_id": "resp_1",
            "source": "provider",
        },
    )

    assert ledger.payload()["transcript"] == [
        {
            "speaker": "candidate",
            "text": "手动输入",
            "turn_id": "local-candidate-1",
            "source": "application",
        },
        {
            "speaker": "assistant",
            "text": "第一段第二段",
            "turn_id": "resp_1",
            "source": "provider",
        },
    ]


def test_ledger_aggregates_audio_packets_without_persisting_each_event():
    ledger = InterviewLedger("iv_test", "demo", "demo", "jd")
    input_data = base64.b64encode(b"i" * 32).decode()
    output_data = base64.b64encode(b"o" * 320).decode()

    for _ in range(150_000):
        ledger.record("client", {"type": "audio.chunk", "data": input_data})
    for _ in range(2_000):
        ledger.record("provider", {"type": "assistant.audio.chunk", "data": output_data})

    payload = ledger.payload()
    assert payload["audio_metrics"] == {
        "input_chunks": 150_000,
        "input_bytes": 4_800_000,
        "output_chunks": 2_000,
        "output_bytes": 640_000,
    }
    assert not [
        row
        for row in payload["events"]
        if row["event"]["type"] in {"audio.chunk", "assistant.audio.chunk"}
    ]
    assert len(json.dumps(payload, ensure_ascii=False)) < 1_000_000
