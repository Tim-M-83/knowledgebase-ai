from app.services.summarizer_language import (
    detect_language_code_from_text,
    get_localized_text,
    resolve_custom_language,
    resolve_response_language,
)


def test_detect_language_code_from_text_detects_german():
    text = (
        "Dieses Dokument beschreibt die wichtigsten Anforderungen für die Einführung des Systems. "
        "Die Mitarbeitenden erhalten eine Übersicht über die Ziele, den Umfang und die nächsten Schritte. "
        "Außerdem werden Risiken, offene Fragen und die geplanten Termine ausführlich erläutert."
    )
    assert detect_language_code_from_text(text) == 'de'


def test_detect_language_code_from_text_detects_english():
    text = (
        "This document explains the main requirements for the rollout of the new system. "
        "The team receives an overview of the goals, scope, timeline, and the most important operational risks. "
        "It also lists the next actions and the responsible stakeholders."
    )
    assert detect_language_code_from_text(text) == 'en'


def test_resolve_response_language_prefers_browser_language_in_auto_mode():
    resolved = resolve_response_language(
        mode='auto',
        custom_response_language=None,
        browser_language='es-ES',
        document_language_code='de',
    )
    assert resolved.code == 'es'
    assert resolved.label == 'Spanish'
    assert resolved.source == 'browser'


def test_resolve_response_language_uses_document_language_when_requested():
    resolved = resolve_response_language(
        mode='document',
        custom_response_language=None,
        browser_language='fr-FR',
        document_language_code='de',
    )
    assert resolved.code == 'de'
    assert resolved.label == 'German'
    assert resolved.source == 'document'


def test_resolve_custom_language_maps_common_aliases():
    label, code = resolve_custom_language('Français')
    assert label == 'French'
    assert code == 'fr'


def test_localized_text_falls_back_to_english_for_unknown_language():
    assert get_localized_text('summary_failed', 'sv') == 'Summary generation failed.'
