import logging
from typing import Iterator
from unittest.mock import patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_bigquery_client() -> Iterator[None]:
    logging.info("Patching google.cloud.bigquery")
    with patch("google.cloud.bigquery.client.Client"):
        yield
