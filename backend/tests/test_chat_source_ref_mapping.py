from types import SimpleNamespace

from app.api.routes.chat import _source_ref_from_row


def test_source_ref_mapping_uses_source_order_as_reference_id():
    row = SimpleNamespace(
        source_order=3,
        document_id=4,
        original_name='policy.pdf',
        chunk_id=88,
        score=0.67,
        page_number=2,
        csv_row_start=None,
        csv_row_end=None,
        snippet='example',
    )
    mapped = _source_ref_from_row(row)
    assert mapped['id'] == 3
    assert mapped['document_id'] == 4
