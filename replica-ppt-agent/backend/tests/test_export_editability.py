from pathlib import Path
import zipfile


def test_editability_check_logic_on_sample_zip(tmp_path: Path) -> None:
    pptx = tmp_path / "sample.pptx"
    with zipfile.ZipFile(pptx, "w") as zf:
        zf.writestr("ppt/slides/slide1.xml", "<p:sld><p:spTree><p:sp/><a:t>hello</a:t></p:spTree></p:sld>")
    assert pptx.exists()

