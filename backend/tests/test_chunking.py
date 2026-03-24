from app.services.chunking import RawSegment, chunk_segments


def test_chunking_overlap_and_metadata():
    text = 'A' * 1000
    chunks = chunk_segments(
        [RawSegment(text=text, metadata={'source_type': 'txt'})],
        chunk_size=300,
        overlap=50,
    )

    assert len(chunks) > 1
    assert chunks[0].metadata['source_type'] == 'txt'
    assert 'snippet' in chunks[0].metadata

    first_tail = chunks[0].content[-50:]
    second_head = chunks[1].content[:50]
    assert first_tail == second_head


def test_chunking_rejects_invalid_sizes():
    try:
        chunk_segments([RawSegment(text='hello', metadata={})], chunk_size=100, overlap=100)
        assert False, 'Expected ValueError'
    except ValueError:
        assert True
