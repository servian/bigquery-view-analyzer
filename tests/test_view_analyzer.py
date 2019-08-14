import re
import pytest

from bigquery_view_analyzer.analyzer import (
    STANDARD_SQL_TABLE_PATTERN,
    LEGACY_SQL_TABLE_PATTERN,
)


standard_table_references = [
    "`project.dataset.table`",
    "`project`.dataset.table",
    "`project.dataset`.table",
    "project.`dataset`.table",
    "project.`dataset.table`",
    "project.dataset.`table`",
    "`project`.`dataset`.`table`",
    "`dataset.table`",
    "`dataset`.table",
    "dataset.`table`",
    "`dataset`.`table`",
    "project.dataset.table",
    "dataset.table",
]

legacy_table_references = ["[project.dataset.table]", "[dataset.table]"]


@pytest.mark.parametrize("table_reference", standard_table_references)
def test_standard_table_pattern(table_reference):
    match = re.search(STANDARD_SQL_TABLE_PATTERN, table_reference, re.IGNORECASE)
    assert match is not None


@pytest.mark.parametrize("table_reference", legacy_table_references)
def test_standard_table_pattern(table_reference):
    match = re.search(LEGACY_SQL_TABLE_PATTERN, table_reference, re.IGNORECASE)
    assert match is not None
