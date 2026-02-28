"""
Unit tests for TTS-only broadcast pipeline feature.

Tests cover:
- Pipeline normalization for tts_only type
- Pipeline validation for tts_only type
- PipelineEntry model with optional STT/LLM
- NoOp adapter behavior
- Template rendering with custom_vars
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.config import PipelineEntry
from src.config.normalization import normalize_pipelines


class TestPipelineEntryTtsOnly:
    """Tests for PipelineEntry model with TTS-only support."""

    def test_standard_pipeline_requires_all_components(self):
        """Standard pipeline with explicit components."""
        entry = PipelineEntry(stt="openai_stt", llm="openai_llm", tts="openai_tts")
        assert entry.stt == "openai_stt"
        assert entry.llm == "openai_llm"
        assert entry.tts == "openai_tts"
        assert entry.type == "standard"
        assert entry.is_tts_only is False

    def test_tts_only_pipeline_type(self):
        """TTS-only pipeline sets type and defaults stt/llm to 'none'."""
        entry = PipelineEntry(type="tts_only", tts="openai_tts")
        assert entry.type == "tts_only"
        assert entry.is_tts_only is True
        assert entry.stt == "none"
        assert entry.llm == "none"
        assert entry.tts == "openai_tts"

    def test_is_tts_only_property(self):
        """is_tts_only property returns correct values."""
        standard = PipelineEntry(stt="local_stt", llm="local_llm", tts="local_tts")
        assert standard.is_tts_only is False

        tts_only = PipelineEntry(type="tts_only", tts="local_tts")
        assert tts_only.is_tts_only is True

    def test_tts_only_pipeline_with_options(self):
        """TTS-only pipeline preserves options."""
        entry = PipelineEntry(
            type="tts_only",
            tts="openai_tts",
            options={"tts": {"voice": "alloy"}},
        )
        assert entry.options["tts"]["voice"] == "alloy"
        assert entry.tools == []


class TestNormalizePipelinesTtsOnly:
    """Tests for normalize_pipelines with TTS-only pipelines."""

    def test_tts_only_normalization(self):
        """TTS-only pipeline should set stt/llm to none_stt/none_llm."""
        config_data = {
            "default_provider": "openai_realtime",
            "pipelines": {
                "broadcast": {
                    "type": "tts_only",
                    "tts": "openai_tts",
                }
            },
        }
        normalize_pipelines(config_data)

        pipeline = config_data["pipelines"]["broadcast"]
        assert pipeline["type"] == "tts_only"
        assert pipeline["stt"] == "none_stt"
        assert pipeline["llm"] == "none_llm"
        assert pipeline["tts"] == "openai_tts"
        assert pipeline["tools"] == []

    def test_tts_only_requires_tts_component(self):
        """TTS-only pipeline without TTS component should raise error."""
        config_data = {
            "default_provider": "openai_realtime",
            "pipelines": {
                "broadcast": {
                    "type": "tts_only",
                    # Missing tts!
                }
            },
        }
        with pytest.raises(TypeError, match="requires a 'tts' component"):
            normalize_pipelines(config_data)

    def test_tts_only_preserves_options(self):
        """TTS-only normalization should preserve options."""
        config_data = {
            "default_provider": "openai_realtime",
            "pipelines": {
                "broadcast": {
                    "type": "tts_only",
                    "tts": "openai_tts",
                    "options": {"tts": {"voice": "nova"}},
                }
            },
        }
        normalize_pipelines(config_data)

        pipeline = config_data["pipelines"]["broadcast"]
        assert pipeline["options"]["tts"]["voice"] == "nova"

    def test_standard_pipeline_still_works(self):
        """Ensure standard pipelines still normalize correctly."""
        config_data = {
            "default_provider": "openai_realtime",
            "pipelines": {
                "main": {
                    "stt": "openai_stt",
                    "llm": "openai_llm",
                    "tts": "openai_tts",
                }
            },
        }
        normalize_pipelines(config_data)

        pipeline = config_data["pipelines"]["main"]
        assert pipeline["type"] == "standard"
        assert pipeline["stt"] == "openai_stt"
        assert pipeline["llm"] == "openai_llm"
        assert pipeline["tts"] == "openai_tts"

    def test_mixed_pipeline_types(self):
        """Standard and TTS-only pipelines can coexist."""
        config_data = {
            "default_provider": "openai_realtime",
            "pipelines": {
                "support": {
                    "stt": "openai_stt",
                    "llm": "openai_llm",
                    "tts": "openai_tts",
                },
                "broadcast": {
                    "type": "tts_only",
                    "tts": "openai_tts",
                },
            },
        }
        normalize_pipelines(config_data)

        assert config_data["pipelines"]["support"]["type"] == "standard"
        assert config_data["pipelines"]["broadcast"]["type"] == "tts_only"
        assert config_data["pipelines"]["broadcast"]["stt"] == "none_stt"


class TestNoOpAdapters:
    """Tests for NoOp STT and LLM adapters."""

    def test_noop_stt_returns_empty_string(self):
        """NoOpSTTAdapter.transcribe should return empty string."""
        import asyncio
        from src.pipelines.orchestrator import NoOpSTTAdapter

        adapter = NoOpSTTAdapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.transcribe("call-1", b"audio", 16000, {})
        )
        assert result == ""

    def test_noop_llm_returns_empty_string(self):
        """NoOpLLMAdapter.generate should return empty string."""
        import asyncio
        from src.pipelines.orchestrator import NoOpLLMAdapter

        adapter = NoOpLLMAdapter()
        result = asyncio.get_event_loop().run_until_complete(
            adapter.generate("call-1", "test", {}, {})
        )
        assert result == ""

    def test_noop_stt_component_key(self):
        """NoOpSTTAdapter should have correct component_key."""
        from src.pipelines.orchestrator import NoOpSTTAdapter

        adapter = NoOpSTTAdapter()
        assert adapter.component_key == "none_stt"

    def test_noop_llm_component_key(self):
        """NoOpLLMAdapter should have correct component_key."""
        from src.pipelines.orchestrator import NoOpLLMAdapter

        adapter = NoOpLLMAdapter()
        assert adapter.component_key == "none_llm"


class TestContextConfigTtsOnly:
    """Tests for ContextConfig TTS-only fields."""

    def test_tts_only_text_field(self):
        """ContextConfig should support tts_only_text."""
        from src.core.transport_orchestrator import ContextConfig

        ctx = ContextConfig(tts_only_text="Hello {name}, your appointment is on {date}.")
        assert ctx.tts_only_text == "Hello {name}, your appointment is on {date}."

    def test_auto_hangup_default_false(self):
        """ContextConfig auto_hangup_after_tts should default to False."""
        from src.core.transport_orchestrator import ContextConfig

        ctx = ContextConfig()
        assert ctx.auto_hangup_after_tts is False

    def test_auto_hangup_explicit_true(self):
        """ContextConfig auto_hangup_after_tts can be set to True."""
        from src.core.transport_orchestrator import ContextConfig

        ctx = ContextConfig(auto_hangup_after_tts=True)
        assert ctx.auto_hangup_after_tts is True


class TestPipelineResolutionTtsOnly:
    """Tests for PipelineResolution is_tts_only field."""

    def test_pipeline_resolution_is_tts_only_default(self):
        """PipelineResolution.is_tts_only should default to False."""
        from src.pipelines.orchestrator import PipelineResolution, NoOpSTTAdapter, NoOpLLMAdapter
        from unittest.mock import MagicMock

        resolution = PipelineResolution(
            call_id="test-call",
            pipeline_name="test",
            stt_key="none_stt",
            stt_adapter=NoOpSTTAdapter(),
            stt_options={},
            llm_key="none_llm",
            llm_adapter=NoOpLLMAdapter(),
            llm_options={},
            tts_key="openai_tts",
            tts_adapter=MagicMock(),
            tts_options={},
        )
        assert resolution.is_tts_only is False

    def test_pipeline_resolution_is_tts_only_true(self):
        """PipelineResolution.is_tts_only can be set to True."""
        from src.pipelines.orchestrator import PipelineResolution, NoOpSTTAdapter, NoOpLLMAdapter
        from unittest.mock import MagicMock

        resolution = PipelineResolution(
            call_id="test-call",
            pipeline_name="broadcast",
            stt_key="none_stt",
            stt_adapter=NoOpSTTAdapter(),
            stt_options={},
            llm_key="none_llm",
            llm_adapter=NoOpLLMAdapter(),
            llm_options={},
            tts_key="openai_tts",
            tts_adapter=MagicMock(),
            tts_options={},
            is_tts_only=True,
        )
        assert resolution.is_tts_only is True
class TestCallSessionTtsOnly:
    """Tests for CallSession model with is_tts_only flag."""

    def test_call_session_is_tts_only_default(self):
        """CallSession.is_tts_only should default to False."""
        from src.core.models import CallSession
        session = CallSession(call_id="test", caller_channel_id="test")
        assert session.is_tts_only is False

    def test_call_session_is_tts_only_true(self):
        """CallSession.is_tts_only can be set to True."""
        from src.core.models import CallSession
        session = CallSession(call_id="test", caller_channel_id="test", is_tts_only=True)
        assert session.is_tts_only is True
