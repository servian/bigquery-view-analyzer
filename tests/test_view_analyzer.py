import re

import pytest
from bqva.analyzer import SQL_TABLE_PATTERN, find_query_objects

valid_standard_table_references = [
    "`project.dataset.table`",
    "`project`.dataset.table",
    "`project.dataset`.table",
    "`project`.`dataset`.`table`",
    "project.dataset.table",
]

invalid_standard_table_references = [
    "`project`.dataset.function()",
    "`dataset.function()`",
    "dataset.function()",
]

legacy_table_references = ["[project:dataset.table]", "[dataset.table]"]
join_prefix = ["", "INNER", "LEFT", "RIGHT", "CROSS", "FULL OUTER"]


@pytest.mark.parametrize("table_a", valid_standard_table_references)
@pytest.mark.parametrize("table_b", valid_standard_table_references)
@pytest.mark.parametrize("join_prefix", join_prefix)
def test_valid_standard_table_reference_in_view(table_a, table_b, join_prefix):
    sql_ddl = """
    SELECT
        table_a.id
        ,table_a.field_a
        ,table_b.field_b
        ,table_b.field_a AS different_field_a
    FROM
        {table_a} AS table_a
    {join_prefix} JOIN
        {table_b} AS table_b
    """.format(
        table_a=table_a, table_b=table_b, join_prefix=join_prefix
    )
    match = re.findall(SQL_TABLE_PATTERN, sql_ddl, re.IGNORECASE | re.MULTILINE)
    assert match is not None
    assert len(match) == 2  # find both table a and b


@pytest.mark.parametrize("table_a", invalid_standard_table_references)
@pytest.mark.parametrize("table_b", invalid_standard_table_references)
@pytest.mark.parametrize("join_prefix", join_prefix)
def test_invalid_standard_table_reference_in_view(table_a, table_b, join_prefix):
    sql_ddl = """
    SELECT
        table_a.id
        ,table_a.field_a
        ,table_b.field_b
        ,table_b.field_a AS different_field_a
    FROM
        {table_a} AS table_a
    {join_prefix} JOIN
        {table_b} AS table_b
    """.format(
        table_a=table_a, table_b=table_b, join_prefix=join_prefix
    )
    match = re.findall(SQL_TABLE_PATTERN, sql_ddl, re.IGNORECASE | re.MULTILINE)
    assert match == []


@pytest.mark.parametrize("table_a", legacy_table_references)
@pytest.mark.parametrize("table_b", legacy_table_references)
@pytest.mark.parametrize("join_prefix", join_prefix)
def test_legacy_table_reference_in_view(table_a, table_b, join_prefix):
    sql_ddl = """
    SELECT
        table_a.id
        ,table_a.field_a
        ,table_b.field_b
        ,table_b.field_a AS different_field_a
    FROM
        {table_a} AS table_a
    {join_prefix} JOIN
        {table_b} AS table_b
    """.format(
        table_a=table_a, table_b=table_b, join_prefix=join_prefix
    )
    match = re.findall(SQL_TABLE_PATTERN, sql_ddl, re.IGNORECASE | re.MULTILINE)
    assert match is not None
    assert len(match) == 2  # find both table a and b


def test_extract_tables_with_single_line_comments():
    sql_ddl = """
    SELECT table_a.id
        --FROM
        --`project.dataset.commented_table` AS commented_table
    FROM
        `project.dataset.table_a` AS table_a
    INNER JOIN
        `project`.dataset.table_b AS table_b"""
    tables = find_query_objects(sql_ddl)
    expected = [("project", "dataset", "table_a"), ("project", "dataset", "table_b")]
    assert tables == expected


def test_extract_tables_with_multiline_comments():
    sql_ddl = """/*
SELECT
  1
FROM
    `project.dataset.faketable1` AS faketable_a
INNER JOIN
    `project`.dataset.faketable2 AS faketable_b
*/
SELECT
    table_a.id
FROM
    `project.dataset.table_a` AS table_a
INNER JOIN
    `project`.dataset.table_b AS table_b"""
    tables = find_query_objects(sql_ddl)
    expected = [("project", "dataset", "table_a"), ("project", "dataset", "table_b")]
    assert tables == expected


def test_extract_tables_with_combination_of_comments():
    sql_ddl = """/*
SELECT
    1
FROM
    `project.dataset.multiline_commented_table` AS faketable_a
*/
SELECT
    2
--FROM
--`project.dataset.single_line_commented_table` AS commented_table
FROM
    `project.dataset.table_a` AS table_a
INNER JOIN
/********
*    FROM
*       `project.dataset.faketable` AS faketable_a
*******/
    `project`.dataset.table_b AS table_b"""
    tables = find_query_objects(sql_ddl)
    expected = [("project", "dataset", "table_a"), ("project", "dataset", "table_b")]
    assert tables == expected
