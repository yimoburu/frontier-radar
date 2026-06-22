import json

from frontier_radar.llm import (
    LLMSettings,
    load_llm_settings,
    synthesize_daily_brief,
)

from test_wiki_render import ranked_item


def test_load_llm_settings_reads_yaml_and_api_key_env(tmp_path):
    config = tmp_path / "llm.yaml"
    config.write_text(
        "enabled: true\n"
        "provider: openai-compatible\n"
        "base_url: https://llm.example/v1\n"
        "model: frontier-synth\n"
        "api_key_env: CUSTOM_LLM_KEY\n"
        "timeout_seconds: 17\n"
        "max_items: 6\n",
        encoding="utf-8",
    )

    settings = load_llm_settings(config, environ={"CUSTOM_LLM_KEY": "secret"})

    assert settings.enabled is True
    assert settings.provider == "openai-compatible"
    assert settings.base_url == "https://llm.example/v1"
    assert settings.model == "frontier-synth"
    assert settings.api_key == "secret"
    assert settings.timeout_seconds == 17
    assert settings.max_items == 6
    assert settings.is_configured is True


def test_load_llm_settings_defaults_to_disabled_when_file_missing(tmp_path):
    settings = load_llm_settings(tmp_path / "missing.yaml", environ={})

    assert settings.enabled is False
    assert settings.is_configured is False


class FakeLLMClient:
    def __init__(self, payload):
        self.payload = payload
        self.messages = None

    def complete_json(self, settings, messages):
        self.settings = settings
        self.messages = messages
        return self.payload


def test_synthesize_daily_brief_uses_configured_llm_with_provenance():
    settings = LLMSettings(
        enabled=True,
        provider="openai-compatible",
        base_url="https://llm.example/v1",
        model="frontier-synth",
        api_key="secret",
        timeout_seconds=30,
        max_items=4,
    )
    client = FakeLLMClient(
        {
            "brief": [
                "Lead: agent memory benchmark changes the eval picture. Provenance: `raw/2026-06-22/arxiv/item.json`",
                "Follow-up: update `wiki/topics/agents.md`. Provenance: `raw/2026-06-22/arxiv/item.json`",
            ]
        }
    )

    result = synthesize_daily_brief(
        [
            ranked_item(
                title="Agent Memory Bench",
                summary="Benchmark claim for agent memory tools.",
                source="arxiv",
                source_type="paper",
                raw_path="raw/2026-06-22/arxiv/item.json",
            )
        ],
        settings,
        client=client,
    )

    assert result.used_llm is True
    assert result.lines == [
        "- Lead: agent memory benchmark changes the eval picture. Provenance: `raw/2026-06-22/arxiv/item.json`",
        "- Follow-up: update `wiki/topics/agents.md`. Provenance: `raw/2026-06-22/arxiv/item.json`",
    ]
    prompt = json.dumps(client.messages)
    assert "Agent Memory Bench" in prompt
    assert "raw/2026-06-22/arxiv/item.json" in prompt


def test_synthesize_daily_brief_reports_missing_key_without_calling_llm():
    settings = LLMSettings(
        enabled=True,
        provider="openai-compatible",
        base_url="https://llm.example/v1",
        model="frontier-synth",
        api_key="",
        timeout_seconds=30,
        max_items=4,
    )
    client = FakeLLMClient({"brief": ["should not be used"]})

    result = synthesize_daily_brief([ranked_item()], settings, client=client)

    assert result.used_llm is False
    assert result.lines is None
    assert "api key" in result.error
    assert client.messages is None


def test_synthesize_daily_brief_replaces_hallucinated_provenance():
    settings = LLMSettings(
        enabled=True,
        provider="openai-compatible",
        base_url="https://llm.example/v1",
        model="frontier-synth",
        api_key="secret",
        timeout_seconds=30,
        max_items=4,
    )
    client = FakeLLMClient(
        {
            "brief": [
                "Lead: useful but cited the wrong file. Provenance: `raw/missing.json`",
            ]
        }
    )

    result = synthesize_daily_brief(
        [
            ranked_item(
                title="Agent Memory Bench",
                raw_path="raw/2026-06-22/arxiv/item.json",
            )
        ],
        settings,
        client=client,
    )

    assert result.lines == [
        "- Lead: useful but cited the wrong file. Provenance: `raw/2026-06-22/arxiv/item.json`"
    ]
