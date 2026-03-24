import re


def normalize_whitespace(text: str) -> str:
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
