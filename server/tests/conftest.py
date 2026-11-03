import os
import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_DIR))

for key in ("GOOGLE_API_KEY", "GROQ_API_KEY", "PINECONE_API_KEY"):
    os.environ.setdefault(key, "test-key")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)
