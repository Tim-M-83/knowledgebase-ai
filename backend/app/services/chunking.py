from dataclasses import dataclass


@dataclass
class RawSegment:
    text: str
    metadata: dict


@dataclass
class ChunkResult:
    chunk_index: int
    content: str
    metadata: dict


def chunk_segments(
    segments: list[RawSegment],
    chunk_size: int = 3800,
    overlap: int = 450,
) -> list[ChunkResult]:
    if chunk_size <= overlap:
        raise ValueError('chunk_size must be greater than overlap')

    output: list[ChunkResult] = []
    cursor = 0

    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                md = dict(segment.metadata)
                md['snippet'] = chunk_text[:200]
                output.append(ChunkResult(chunk_index=cursor, content=chunk_text, metadata=md))
                cursor += 1
            if end >= len(text):
                break
            start = end - overlap
    return output
