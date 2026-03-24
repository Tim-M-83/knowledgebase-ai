from app.api.routes.chat import LOW_CONFIDENCE_WARNING, chat_warning


def test_warning_when_sources_and_low_confidence():
    assert chat_warning(has_sources=True, low_confidence=True) == LOW_CONFIDENCE_WARNING


def test_no_warning_without_sources():
    assert chat_warning(has_sources=False, low_confidence=True) is None


def test_no_warning_when_confident():
    assert chat_warning(has_sources=True, low_confidence=False) is None
