import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from pypdf import PdfWriter

from modules import load_vectorstore as lv


def _upload(name: str, content: bytes):
    f = MagicMock()
    f.filename = name
    f.file = io.BytesIO(content)
    return f


def _blank_pdf(password: str | None = None) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    if password is not None:
        writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_load_pdf_reads_pages_with_metadata():
    pages = [MagicMock(), MagicMock()]
    pages[0].extract_text.return_value = "La metformine est un antidiabétique."
    pages[1].extract_text.return_value = None

    with patch.object(lv, "PdfReader") as reader:
        reader.return_value.is_encrypted = False
        reader.return_value.pages = pages
        docs = lv.load_pdf("some/dir/any.pdf")

    assert len(docs) == 2
    assert docs[0].metadata == {"source": "any.pdf", "page": 0}
    assert "metformine" in docs[0].page_content
    assert docs[1].page_content == ""


def test_load_pdf_rejects_invalid_file(tmp_path):
    path = tmp_path / "bad.pdf"
    path.write_bytes(b"not a pdf at all")
    with pytest.raises(lv.PDFProcessingError, match="pas un PDF valide"):
        lv.load_pdf(path)


def test_load_pdf_rejects_password_protected(tmp_path):
    path = tmp_path / "locked.pdf"
    path.write_bytes(_blank_pdf(password="secret"))
    with pytest.raises(lv.PDFProcessingError, match="mot de passe"):
        lv.load_pdf(path)


def test_doc_id_prefix_is_ascii_and_stable():
    prefix = lv.doc_id_prefix("résumé médical.pdf")
    assert prefix.isascii() and prefix.endswith("#")
    assert prefix == lv.doc_id_prefix("résumé médical.pdf")
    assert prefix != lv.doc_id_prefix("autre.pdf")


def test_load_vectorstore_reports_scanned_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(lv, "UPLOAD_DIR", str(tmp_path))
    result = lv.load_vectorstore([_upload("scan.pdf", _blank_pdf())])
    assert result["processed"] == {}
    assert "OCR" in result["errors"]["scan.pdf"]
    assert not (tmp_path / "scan.pdf").exists()


def test_load_vectorstore_strips_directories_from_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(lv, "UPLOAD_DIR", str(tmp_path))
    with patch.object(lv, "index_pdf", return_value=3) as index_pdf:
        result = lv.load_vectorstore([_upload("../../evil.pdf", b"%PDF")])
    assert result == {"processed": {"evil.pdf": 3}, "errors": {}}
    index_pdf.assert_called_once_with(Path(tmp_path) / "evil.pdf")


def test_index_pdf_replaces_old_chunks_and_batches(monkeypatch):
    text = "mot " * 20_000  # ~80k chars -> well over one batch of 500-char chunks
    monkeypatch.setattr(lv, "load_pdf", lambda _: [Document(page_content=text, metadata={"source": "big.pdf", "page": 0})])
    monkeypatch.setattr(lv, "is_medical_document", lambda docs: True)
    vectorstore = MagicMock()
    vectorstore.index.list.return_value = iter([["old#0", "old#1"]])
    monkeypatch.setattr(lv, "get_vectorstore", lambda: vectorstore)

    n = lv.index_pdf(Path("big.pdf"))

    vectorstore.index.delete.assert_called_once_with(ids=["old#0", "old#1"])
    calls = vectorstore.add_documents.call_args_list
    assert len(calls) > 1
    assert all(len(c.args[0]) <= lv.BATCH_SIZE for c in calls)
    all_ids = [i for c in calls for i in c.kwargs["ids"]]
    assert len(all_ids) == n and len(set(all_ids)) == n
    assert all(i.startswith(lv.doc_id_prefix("big.pdf")) for i in all_ids)

    
def test_index_pdf_rejects_non_medical_document(monkeypatch):
    monkeypatch.setattr(lv, "load_pdf", lambda _: [Document(page_content="recette de gâteau", metadata={"source": "x.pdf", "page": 0})])
    monkeypatch.setattr(lv, "is_medical_document", lambda docs: False)
    vectorstore = MagicMock()
    monkeypatch.setattr(lv, "get_vectorstore", lambda: vectorstore)

    with pytest.raises(lv.PDFProcessingError):
        lv.index_pdf(Path("x.pdf"))

    vectorstore.index.delete.assert_not_called()      # l'ancienne version n'est pas effacée
    vectorstore.add_documents.assert_not_called()