import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models.summarizer import SummarizerChunk, SummarizerDocument


SummarizerResponseLanguageMode = Literal['auto', 'document', 'custom']

SUPPORTED_LANGUAGE_LABELS: dict[str, str] = {
    'de': 'German',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'it': 'Italian',
    'nl': 'Dutch',
    'pt': 'Portuguese',
}

LANGUAGE_ALIAS_MAP: dict[str, tuple[str, str]] = {
    'de': ('de', 'German'),
    'deutsch': ('de', 'German'),
    'german': ('de', 'German'),
    'en': ('en', 'English'),
    'eng': ('en', 'English'),
    'english': ('en', 'English'),
    'es': ('es', 'Spanish'),
    'espanol': ('es', 'Spanish'),
    'espanol latinoamericano': ('es', 'Spanish'),
    'español': ('es', 'Spanish'),
    'spanish': ('es', 'Spanish'),
    'fr': ('fr', 'French'),
    'francais': ('fr', 'French'),
    'français': ('fr', 'French'),
    'french': ('fr', 'French'),
    'it': ('it', 'Italian'),
    'italian': ('it', 'Italian'),
    'italiano': ('it', 'Italian'),
    'nl': ('nl', 'Dutch'),
    'dutch': ('nl', 'Dutch'),
    'nederlands': ('nl', 'Dutch'),
    'pt': ('pt', 'Portuguese'),
    'portuguese': ('pt', 'Portuguese'),
    'portugues': ('pt', 'Portuguese'),
    'português': ('pt', 'Portuguese'),
}

LOCALIZED_TEXT: dict[str, dict[str, str]] = {
    'de': {
        'low_confidence_warning': 'Antwort mit niedriger Retrieval-Sicherheit erzeugt. Bitte mit dem Dokumentinhalt abgleichen.',
        'no_context_answer': 'Ich finde in diesem hochgeladenen Dokument nicht genug relevanten Kontext, um deine Frage sicher zu beantworten. Bitte stelle eine konkretere Frage.',
        'chat_error': 'Die Dokumentfrage konnte nicht abgeschlossen werden.',
        'document_not_ready': 'Das Dokument ist noch nicht bereit.',
        'no_summary_content': 'Keine indizierten Inhalte für die Zusammenfassung verfügbar.',
        'summary_failed': 'Die Zusammenfassung konnte nicht erstellt werden.',
        'summary_query': 'Fasse die wichtigsten Informationen in diesem Dokument zusammen.',
    },
    'en': {
        'low_confidence_warning': 'Answer generated with low retrieval confidence. Verify against the document context.',
        'no_context_answer': 'I cannot find enough relevant context in this uploaded document to answer your question confidently. Please ask a more specific question.',
        'chat_error': 'Unable to complete summarizer chat request.',
        'document_not_ready': 'Document is not ready yet.',
        'no_summary_content': 'No indexed content available for summarization.',
        'summary_failed': 'Summary generation failed.',
        'summary_query': 'Summarize the most important information in this document.',
    },
    'es': {
        'low_confidence_warning': 'Respuesta generada con baja confianza de recuperación. Verifica el contenido con el documento.',
        'no_context_answer': 'No puedo encontrar suficiente contexto relevante en este documento cargado para responder con confianza. Haz una pregunta más específica.',
        'chat_error': 'No se pudo completar la consulta sobre el documento.',
        'document_not_ready': 'El documento todavía no está listo.',
        'no_summary_content': 'No hay contenido indexado disponible para generar el resumen.',
        'summary_failed': 'No se pudo generar el resumen.',
        'summary_query': 'Resume la información más importante de este documento.',
    },
    'fr': {
        'low_confidence_warning': 'Réponse générée avec une faible confiance de récupération. Vérifiez-la avec le contenu du document.',
        'no_context_answer': "Je ne trouve pas assez de contexte pertinent dans ce document importé pour répondre avec confiance. Posez une question plus précise.",
        'chat_error': "Impossible de terminer la question sur le document.",
        'document_not_ready': "Le document n'est pas encore prêt.",
        'no_summary_content': 'Aucun contenu indexé disponible pour générer le résumé.',
        'summary_failed': 'La génération du résumé a échoué.',
        'summary_query': 'Résume les informations les plus importantes de ce document.',
    },
    'it': {
        'low_confidence_warning': 'Risposta generata con bassa confidenza di recupero. Verificala rispetto al contenuto del documento.',
        'no_context_answer': 'Non riesco a trovare abbastanza contesto pertinente in questo documento caricato per rispondere con sicurezza. Fai una domanda più specifica.',
        'chat_error': 'Impossibile completare la richiesta sul documento.',
        'document_not_ready': 'Il documento non è ancora pronto.',
        'no_summary_content': 'Nessun contenuto indicizzato disponibile per il riepilogo.',
        'summary_failed': 'Generazione del riepilogo non riuscita.',
        'summary_query': 'Riassumi le informazioni più importanti di questo documento.',
    },
    'nl': {
        'low_confidence_warning': 'Antwoord gegenereerd met lage retrieval-betrouwbaarheid. Controleer dit aan de hand van het document.',
        'no_context_answer': 'Ik kan niet genoeg relevante context in dit geuploade document vinden om je vraag met vertrouwen te beantwoorden. Stel een specifiekere vraag.',
        'chat_error': 'Kan de documentvraag niet voltooien.',
        'document_not_ready': 'Het document is nog niet gereed.',
        'no_summary_content': 'Geen geïndexeerde inhoud beschikbaar voor samenvatting.',
        'summary_failed': 'Samenvatten mislukt.',
        'summary_query': 'Vat de belangrijkste informatie uit dit document samen.',
    },
    'pt': {
        'low_confidence_warning': 'Resposta gerada com baixa confiança de recuperação. Verifique com o conteúdo do documento.',
        'no_context_answer': 'Não consigo encontrar contexto relevante suficiente neste documento enviado para responder com confiança. Faça uma pergunta mais específica.',
        'chat_error': 'Não foi possível concluir a pergunta sobre o documento.',
        'document_not_ready': 'O documento ainda não está pronto.',
        'no_summary_content': 'Nenhum conteúdo indexado disponível para resumir.',
        'summary_failed': 'Falha ao gerar o resumo.',
        'summary_query': 'Resuma as informações mais importantes deste documento.',
    },
}

LANGUAGE_STOPWORDS: dict[str, set[str]] = {
    'de': {'der', 'die', 'das', 'und', 'ist', 'nicht', 'mit', 'den', 'von', 'auf', 'für', 'eine', 'einer', 'einem', 'auch', 'als', 'bei', 'wird', 'oder', 'zum', 'zur', 'im', 'des', 'dem'},
    'en': {'the', 'and', 'for', 'that', 'with', 'this', 'from', 'are', 'was', 'were', 'have', 'has', 'you', 'your', 'into', 'about', 'will', 'they', 'their', 'not', 'can', 'more', 'than'},
    'es': {'el', 'la', 'los', 'las', 'una', 'uno', 'unos', 'unas', 'de', 'del', 'que', 'para', 'con', 'por', 'como', 'más', 'pero', 'sus', 'este', 'esta', 'también', 'entre', 'sobre', 'sin'},
    'fr': {'le', 'la', 'les', 'des', 'une', 'un', 'pour', 'avec', 'dans', 'sur', 'par', 'pas', 'plus', 'est', 'sont', 'vous', 'nous', 'qui', 'que', 'ces', 'aux', 'des', 'du', 'elle'},
    'it': {'il', 'lo', 'la', 'gli', 'le', 'per', 'con', 'del', 'della', 'delle', 'che', 'non', 'piu', 'più', 'una', 'uno', 'questo', 'questa', 'sono', 'come', 'anche', 'nel', 'nella', 'degli'},
    'nl': {'de', 'het', 'een', 'en', 'van', 'voor', 'met', 'niet', 'dat', 'dit', 'zijn', 'wordt', 'ook', 'als', 'bij', 'door', 'meer', 'dan', 'over', 'onder', 'naar', 'tussen'},
    'pt': {'de', 'do', 'da', 'dos', 'das', 'para', 'com', 'que', 'uma', 'um', 'como', 'mais', 'não', 'na', 'no', 'nos', 'nas', 'por', 'sobre', 'entre', 'tambem', 'também'},
}

LANGUAGE_CHAR_HINTS: dict[str, tuple[str, ...]] = {
    'de': ('ä', 'ö', 'ü', 'ß'),
    'es': ('á', 'é', 'í', 'ó', 'ú', 'ñ', '¿', '¡'),
    'fr': ('à', 'â', 'ç', 'é', 'è', 'ê', 'ë', 'î', 'ï', 'ô', 'ù', 'û', 'œ'),
    'it': ('à', 'è', 'é', 'ì', 'ò', 'ù'),
    'pt': ('ã', 'õ', 'ç', 'á', 'â', 'ê', 'ô', 'ú'),
}

TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ']+")
MAX_LANGUAGE_SAMPLE_CHARS = 4000


@dataclass(frozen=True)
class ResolvedSummarizerLanguage:
    label: str
    code: str
    source: str


def _strip_accents(value: str) -> str:
    return ''.join(
        char for char in unicodedata.normalize('NFKD', value) if not unicodedata.combining(char)
    )


def normalize_language_code(value: str | None) -> str | None:
    if not value:
        return None
    primary = value.strip().split('-', 1)[0].split('_', 1)[0].lower()
    return primary if primary in SUPPORTED_LANGUAGE_LABELS else None


def resolve_custom_language(value: str | None) -> tuple[str, str | None]:
    cleaned = (value or '').strip()
    if not cleaned:
        return ('English', 'en')

    alias = _strip_accents(cleaned).lower()
    if alias in LANGUAGE_ALIAS_MAP:
        code, label = LANGUAGE_ALIAS_MAP[alias]
        return (label, code)
    return (cleaned, None)


def resolve_response_language(
    *,
    mode: SummarizerResponseLanguageMode,
    custom_response_language: str | None,
    browser_language: str | None,
    document_language_code: str | None,
) -> ResolvedSummarizerLanguage:
    browser_code = normalize_language_code(browser_language)
    document_code = normalize_language_code(document_language_code)

    if mode == 'custom':
        label, code = resolve_custom_language(custom_response_language)
        return ResolvedSummarizerLanguage(label=label, code=code or 'en', source='custom')

    if mode == 'document':
        if document_code:
            return ResolvedSummarizerLanguage(
                label=SUPPORTED_LANGUAGE_LABELS[document_code],
                code=document_code,
                source='document',
            )
        return ResolvedSummarizerLanguage(label='English', code='en', source='fallback')

    if browser_code:
        return ResolvedSummarizerLanguage(
            label=SUPPORTED_LANGUAGE_LABELS[browser_code],
            code=browser_code,
            source='browser',
        )
    if document_code:
        return ResolvedSummarizerLanguage(
            label=SUPPORTED_LANGUAGE_LABELS[document_code],
            code=document_code,
            source='document',
        )
    return ResolvedSummarizerLanguage(label='English', code='en', source='fallback')


def get_localized_text(key: str, language_code: str | None) -> str:
    code = normalize_language_code(language_code) or 'en'
    return LOCALIZED_TEXT.get(code, LOCALIZED_TEXT['en']).get(key, LOCALIZED_TEXT['en'][key])


def build_summary_prompt(target_language: str) -> str:
    return (
        'You are an AI document summarizer for external documents. '
        'Use only the provided context from this single document.\n\n'
        f'Write the entire answer in {target_language}. Do not switch to English unless {target_language} is English.\n'
        'Return Markdown with the following section meanings, but translate all section headings into the response language:\n'
        '- Executive Summary\n'
        '- Most Important Information\n'
        '- Key Facts and Figures\n'
        '- Risks or Open Questions (only when needed)\n\n'
        'If the context is insufficient, say that clearly in the requested response language.'
    )


def build_document_chat_prompt(target_language: str) -> str:
    return (
        'You answer questions about one uploaded external document only. '
        'Use only the provided context chunks and do not use company knowledge.\n\n'
        f'Answer entirely in {target_language}. Do not switch to English unless {target_language} is English.\n'
        'Response rules:\n'
        '- Be concise and practical.\n'
        '- Cite evidence inline with [n] references.\n'
        '- If the answer is not in the document context, say that clearly in the requested response language.'
    )


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def detect_language_code_from_text(text: str) -> str | None:
    sample = text.strip().lower()
    if len(sample) < 120:
        return None

    tokens = _tokenize(sample)
    if len(tokens) < 20:
        return None

    scores: dict[str, float] = {}
    for language_code, stopwords in LANGUAGE_STOPWORDS.items():
        score = float(sum(1 for token in tokens if token in stopwords))
        char_hints = LANGUAGE_CHAR_HINTS.get(language_code, ())
        score += sum(sample.count(marker) * 0.75 for marker in char_hints)
        scores[language_code] = score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_code, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if top_score < 3 or top_score < second_score + 1:
        return None
    return top_code


def detect_language_code_from_texts(texts: list[str]) -> str | None:
    combined: list[str] = []
    total = 0
    for text in texts:
        if not text:
            continue
        remaining = MAX_LANGUAGE_SAMPLE_CHARS - total
        if remaining <= 0:
            break
        snippet = text[:remaining]
        combined.append(snippet)
        total += len(snippet)
    return detect_language_code_from_text('\n'.join(combined))


def ensure_document_language_code(db: Session, document: SummarizerDocument) -> str | None:
    existing = normalize_language_code(document.detected_language_code)
    if existing:
        return existing

    rows = (
        db.query(SummarizerChunk.content)
        .filter(SummarizerChunk.document_id == document.id)
        .order_by(SummarizerChunk.chunk_index.asc())
        .limit(8)
        .all()
    )
    detected = detect_language_code_from_texts([row[0] for row in rows if row and row[0]])
    if detected:
        document.detected_language_code = detected
        db.commit()
        db.refresh(document)
    return detected
