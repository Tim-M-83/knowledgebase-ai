from app.schemas.personal_note import PersonalNoteCreate, PersonalNoteOut, PersonalNoteUpdate


def test_personal_note_schema_fields():
    out_fields = set(PersonalNoteOut.model_fields.keys())
    assert {'id', 'user_id', 'title', 'content', 'priority', 'created_at', 'updated_at'}.issubset(out_fields)

    create_fields = set(PersonalNoteCreate.model_fields.keys())
    update_fields = set(PersonalNoteUpdate.model_fields.keys())
    assert create_fields == {'title', 'content', 'priority'}
    assert update_fields == {'title', 'content', 'priority'}
