"""Make Hugging Face ASR pipeline skip TorchCodec when the package is present but unusable.

``pyannote-audio`` pulls in ``torchcodec``; ``transformers`` then does a top-level
``import torchcodec`` inside ``AutomaticSpeechRecognitionPipeline.preprocess`` whenever
the package is installed—before it inspects inputs. On Windows that often fails to load
native DLLs. Local decoding (e.g. ``soundfile``) does not need TorchCodec; call this
**before** ``from transformers import ... pipeline``.
"""


def disable_torchcodec_probe_for_asr() -> None:
    def _torchcodec_unavailable() -> bool:
        return False

    from transformers.utils import import_utils  # noqa: PLC0415

    import_utils.is_torchcodec_available = _torchcodec_unavailable  # type: ignore[assignment]

    try:
        import transformers.pipelines.automatic_speech_recognition as asr_module  # noqa: PLC0415

        asr_module.is_torchcodec_available = _torchcodec_unavailable  # type: ignore[assignment]
    except ImportError:  # noqa: S110
        pass
