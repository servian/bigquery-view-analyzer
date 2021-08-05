import logging
import re
from typing import Iterable, List, Optional, Tuple, cast

from anytree import LevelOrderIter, NodeMixin
from google.cloud import bigquery
from google.cloud.bigquery import AccessEntry, Dataset, Table

SQL_TABLE_PATTERN = r"(?:(?:FROM|JOIN)\s+?)[\x60\[]?(?:(?P<project>[\w][-\w]+?)\x60?[\:\.])?\x60?(?P<dataset>[\w]+?)\x60?\.\x60?(?P<table>[\w]+)[\x60\]]?(?:\s|$)"
COMMENTS_PATTERN = r"(\/\*(.|[\r\n])*?\*\/)|(--.*)"

log = logging.getLogger("bqva.analyzer")


def find_query_objects(query) -> List[Tuple[Optional[str], str, str]]:
    # Remove comments from query to avoid picking up tables from commented out SQL code
    view_query = re.sub(COMMENTS_PATTERN, "", query)
    tables = re.findall(SQL_TABLE_PATTERN, view_query, re.IGNORECASE | re.MULTILINE)
    return tables


class TableNode(NodeMixin):
    table: Table
    parent: Optional["TableNode"]
    children: List[Optional["TableNode"]]

    def __init__(
        self,
        client: bigquery.Client,
        table: Table,
        parent: Optional["TableNode"] = None,
        children=None,
    ):
        super().__init__()
        self.client = client
        self.table = table
        self.parent = parent
        if children:
            self.children = children

    def __repr__(self) -> str:
        return "TableNode({})".format(self.name)

    @property
    def name(self) -> str:
        if not self.table.full_table_id:
            raise ValueError("table.full_table_id unknown")
        return self.table.full_table_id

    @property
    def project(self) -> str:
        if not self.table.project:
            raise ValueError("table.project unknown")
        return cast(str, self.table.project)

    @property
    def dataset_id(self) -> str:
        if not self.table.dataset_id:
            raise ValueError("table.dataset_id unknown")
        return cast(str, self.table.dataset_id)

    @property
    def table_id(self) -> str:
        if not self.table.table_id:
            raise ValueError("table.table_id unknown")
        return cast(str, self.table.table_id)

    @property
    def access_entry(self) -> AccessEntry:
        return AccessEntry(
            role=None, entity_type="view", entity_id=self.table.reference.to_api_repr()
        )

    @property
    def dataset(self) -> Dataset:
        dataset_ref = self.client.dataset(self.dataset_id, project=self.project)
        return self.client.get_dataset(dataset_ref)

    def parent_child_share_dataset(self) -> Optional[bool]:
        if not self.parent:
            return None
        return (
            self.parent.dataset_id == self.dataset_id
            and self.parent.project == self.project
        )

    def is_authorized(self) -> Optional[bool]:
        if not self.parent:
            return None
        elif (
            self.dataset_id == self.parent.dataset_id
            and self.project == self.parent.project
        ):
            # no action required if within same dataset
            return True
        else:
            parent_entity_id = self.parent.table.reference.to_api_repr()
            access_entries = self.dataset.access_entries
            return parent_entity_id in [ae.entity_id for ae in access_entries]

    def authorize_view(self, view_node: "TableNode"):
        log.info(
            f"{self.name}: authorizing view '{view_node.name}' with dataset '{self.dataset.full_dataset_id}'"
        )
        dataset = self.dataset  # mutable copy
        access_entries = dataset.access_entries
        access_entries.append(view_node.access_entry)
        dataset.access_entries = access_entries
        self.client.update_dataset(dataset, ["access_entries"])

    def revoke_view(self, view_node: "TableNode"):
        dataset = self.dataset  # mutable copy
        access_entries = dataset.access_entries
        for i, ae in enumerate(access_entries):
            if view_node.access_entry.entity_id == ae.entity_id:
                log.info(
                    f"{self.name}: revoking view '{view_node.name}' from dataset '{self.dataset.full_dataset_id}'"
                )
                access_entries.pop(i)
                break
        dataset.access_entries = access_entries
        self.client.update_dataset(dataset, ["access_entries"])


class ViewAnalyzer:
    def __init__(
        self,
        dataset_id: str,
        view_id: str,
        project_id: str = None,
        client: bigquery.Client = None,
    ):
        if client is None:
            self.client = bigquery.Client()
        project_id = project_id or self.client.project
        log.info(f"Analysing view: {project_id}.{dataset_id}.{view_id}")
        view = self._get_table(project_id, dataset_id, view_id)
        assert view.table_type == "VIEW"
        self.view = view

    def __str__(self):
        return self.view.full_table_id

    @property
    def tree(self) -> TableNode:
        if not hasattr(self, "_tree"):
            root_node = TableNode(client=self.client, table=self.view)
            self._tree = self._build_tree(root_node)
        return self._tree

    def _get_table(self, project_id: str, dataset_id: str, table_id: str) -> Table:
        dataset_ref = self.client.dataset(dataset_id, project=project_id)
        view_ref = dataset_ref.table(table_id)
        return self.client.get_table(view_ref)

    def _build_tree(self, node: TableNode) -> TableNode:
        table = node.table
        log.info(f"{node.name}")
        log.info(f"{node.name}: object is of type {table.table_type}")
        if table.table_type == "VIEW":
            tables = find_query_objects(table.view_query)
            count = len(tables)
            log.info(f"{node.name}: found {count} related objects in view query")
            for i, t in enumerate(tables, start=1):
                project_id, dataset_id, table_id = t
                if project_id is None:
                    # assume table shares same project as encompassing view
                    project_id = cast(str, table.project)
                child_table = self._get_table(project_id, dataset_id, table_id)
                child_node = TableNode(
                    client=self.client, table=child_table, parent=node
                )
                log.info(f"{node.name}: analyzing '{child_node.name}' ({i}/{count})")
                self._build_tree(child_node)
        return node

    def apply_permissions(self):
        log.info("Applying permissions...")
        for node in cast(Iterable[TableNode], LevelOrderIter(self.tree)):
            if not node.parent:
                continue
            elif node.is_authorized():
                log.info(
                    f"{node.name}: parent object '{node.parent.name}' is already authorized"
                )
            else:
                node.authorize_view(node.parent)

    def revoke_permissions(self):
        log.info("Revoking permissions...")
        for node in cast(Iterable[TableNode], LevelOrderIter(self.tree)):
            if node.parent and node.is_authorized():
                node.revoke_view(node.parent)
