from pypdf import PdfReader

from exporter.exporters.pdf_export import PdfExporter


def test_pdf_export(bundle, tmp_path):
    paths = PdfExporter().export(bundle, tmp_path)
    assert len(paths) == len(bundle.conversations)
    for p in paths:
        assert p.exists() and p.stat().st_size > 800

    alice_pdf = next(p for p in paths if p.name.startswith("Alice Client"))
    text = "\n".join(page.extract_text() for page in PdfReader(alice_pdf).pages)
    assert "Alice Client" in text
    assert "goldendoodle" in text
    assert "10am works great" in text
    assert "March" in text                      # day separator rendered
    assert "(925) 897-9008" in text             # owner number in header
    assert "Loved an image" not in text         # tapback skipped


def test_long_message_spans_pages(bundle, tmp_path):
    paths = PdfExporter().export(bundle, tmp_path)
    unnamed_group = next(
        p for p in paths
        if p.name.split("-")[-1] == "4.pdf")
    reader = PdfReader(unnamed_group)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "full care instructions" in text


def test_group_pdf_shows_sender_names(bundle, tmp_path):
    paths = PdfExporter().export(bundle, tmp_path)
    wedding = next(p for p in paths if p.name.startswith("Wedding Crew"))
    text = "\n".join(page.extract_text() for page in PdfReader(wedding).pages)
    assert "Carol Cakes LLC" in text
