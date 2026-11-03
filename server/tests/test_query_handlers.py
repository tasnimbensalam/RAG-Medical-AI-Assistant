from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from modules.query_handlers import query_chain


def test_query_chain_formats_response():
    chain = MagicMock()
    chain.invoke.return_value = {
        "answer": "An answer",
        "context": [Document(page_content="x", metadata={"source": "a.pdf"})],
    }
    assert query_chain(chain, "q") == {"response": "An answer", "sources": ["a.pdf"]}


def test_query_chain_reraises_errors():
    chain = MagicMock()
    chain.invoke.side_effect = RuntimeError("boom")
    with pytest.raises(RuntimeError):
        query_chain(chain, "q")
