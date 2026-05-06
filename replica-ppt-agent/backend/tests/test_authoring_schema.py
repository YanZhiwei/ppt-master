from app.authoring.schema import validate_authoring_document


def test_authoring_schema_valid() -> None:
    ok, err = validate_authoring_document(
        {
            "slide_id": "slide-1",
            "title": "Cover",
            "width": 1280,
            "height": 720,
            "background": "#FFFFFF",
            "objects": [
                {
                    "id": "obj-title",
                    "type": "textbox",
                    "x": 100,
                    "y": 100,
                    "width": 600,
                    "height": 120,
                    "text": "Hello",
                    "style": {"fontSize": 48},
                }
            ],
        }
    )
    assert ok is True
    assert err is None


def test_authoring_schema_invalid_without_objects() -> None:
    ok, err = validate_authoring_document(
        {"slide_id": "slide-1", "title": "Cover", "width": 1280, "height": 720, "objects": []}
    )
    assert ok is False
    assert err is not None

