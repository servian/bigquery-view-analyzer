import sys
import logging
import re
from typing import Optional

import google.auth
from anytree import LevelOrderIter, NodeMixin, RenderTree
from colorama import Fore, init
from google.cloud import bigquery
from google.cloud.bigquery import Table, AccessEntry, Dataset

STANDARD_SQL_TABLE_PATTERN = r"(?:(?:FROM|JOIN)\s+?)?`(?P<project>[-\w]+?)`?\.`?(?P<dataset>[\w]+?)`?\.`?(?P<table>[\w]+)`?(?!\()\b"
LEGACY_SQL_TABLE_PATTERN = r"(?:(?:FROM|JOIN)\s+?)?\[(?:(?P<project>[-\w]+?)(?:\:))?(?P<dataset>[-\w]+?)\.(?P<table>[-\w]+?)\]"
COMMENTS_PATTERN = r"(\/\*(.|[\r\n])*?\*\/)|(--.*)"

log = logging.getLogger("bqva.analyzer")
init(autoreset=True)

try:
    client = bigquery.Client()
except google.auth.exceptions.DefaultCredentialsError as e:
    log.error(e)
    sys.exit(1)


class TableNode(NodeMixin):
    def __init__(
        self, table: Table, parent: Optional["TableNode"] = None, children=None
    ):
        super().__init__()
        self.table = table
        self.parent = parent
        if children:
            self.children = children

    @property
    def name(self) -> str:
        return self.table.full_table_id

    @property
    def access_entry(self) -> AccessEntry:
        return AccessEntry(
            role=None, entity_type="view", entity_id=self.table.reference.to_api_repr()
        )

    @property
    def dataset(self) -> Dataset:
        dataset_ref = client.dataset(self.table.dataset_id, project=self.table.project)
        return client.get_dataset(dataset_ref)

    def pretty_name(self, show_authorization_status=False) -> str:
        table_color = Fore.GREEN if self.table.table_type == "VIEW" else Fore.RED
        name_parts = {
            "project": Fore.CYAN + self.table.project + Fore.RESET,
            "dataset": Fore.YELLOW + self.table.dataset_id + Fore.RESET,
            "table": table_color + self.table.table_id + Fore.RESET,
        }
        name = "{}:{}.{}".format(
            name_parts["project"], name_parts["dataset"], name_parts["table"]
        )
        is_authorized = self.is_authorized()
        if show_authorization_status and is_authorized is not None:
            status_color = Fore.GREEN if is_authorized else Fore.RED
            status = status_color + ("✓" if is_authorized else "⨯") + Fore.RESET
            name += " ({})".format(status)
        return name

    def parent_child_share_dataset(self) -> bool:
        return (
            self.parent.dataset.dataset_id == self.table.dataset_id
            and self.parent.dataset.project == self.table.project
        )

    def is_authorized(self) -> Optional[bool]:
        if self.parent:
            if self.parent_child_share_dataset():
                # default behaviour allows access to tables within the same dataset as the parent view
                return True
            else:
                parent_entity_id = self.parent.table.reference.to_api_repr()
                access_entries = self.dataset.access_entries
                return parent_entity_id in [ae.entity_id for ae in access_entries]
        return None

    def authorize_view(self, view_node: "TableNode"):
        log.info(
            f"{self.name}: authorizing view '{view_node.name}' with dataset '{self.dataset.full_dataset_id}'"
        )
        dataset = self.dataset  # mutable copy
        access_entries = dataset.access_entries
        access_entries.append(view_node.access_entry)
        dataset.access_entries = access_entries
        client.update_dataset(dataset, ["access_entries"])

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
        client.update_dataset(dataset, ["access_entries"])

    def __repr__(self) -> str:
        return "TableNode({})".format(self.name)


class ViewAnalyzer:
    def __init__(self, dataset_id: str, view_id: str, project_id: str = None):
        project_id = project_id or client.project
        log.info(f"Analysing view: {project_id}.{dataset_id}.{view_id}")
        view = self._get_table(project_id, dataset_id, view_id)
        assert view.table_type == "VIEW"
        self.view = view

    def __str__(self):
        return self.view.full_table_id

    @property
    def tree(self) -> TableNode:
        if not hasattr(self, "_tree"):
            root_node = TableNode(table=self.view)
            self._tree = self._build_tree(root_node)
        return self._tree

    def apply_permissions(self):
        log.info(f"Applying permissions...")
        for node in LevelOrderIter(self.tree):
            if not node.parent:
                continue
            if node.parent_child_share_dataset():
                log.info(
                    f"{node.name}: parent object '{node.parent.name}' is in same project/dataset, no action required"
                )
            else:
                is_authorized = node.is_authorized()
                log.info(
                    f"{node.name}: parent object '{node.parent.name}' is {'NOT' if not is_authorized else ''}currently authorized"
                )
                if not is_authorized:
                    node.authorize_view(node.parent)

    def revoke_permissions(self):
        log.info(f"Revoking permissions...")
        for node in LevelOrderIter(self.tree):
            if not node.parent:
                continue
            if node.parent_child_share_dataset():
                log.info(
                    f"{node.name}: parent object '{node.parent.name}' is in same project/dataset, no action required"
                )
            elif node.is_authorized():
                node.revoke_view(node.parent)

    def format_tree(self, show_key=False, show_status=False):
        log.info(f"Formatting tree...")
        tree_string = ""
        key = {
            "project": (Fore.CYAN + "◉" + Fore.RESET + " = Project".ljust(12)),
            "dataset": (Fore.YELLOW + "◉" + Fore.RESET + " = Dataset".ljust(12)),
            "table": (Fore.RED + "◉" + Fore.RESET + " = Table".ljust(12)),
            "view": (Fore.GREEN + "◉" + Fore.RESET + " = View".ljust(12)),
        }
        if show_key:
            tree_string += "Key:\n{}{}\n{}{}\n\n".format(
                key["project"], key["table"], key["dataset"], key["view"]
            )
        for pre, _, node in RenderTree(self.tree):
            tree_string += "%s%s\n" % (
                pre,
                node.pretty_name(show_authorization_status=show_status),
            )
        return tree_string

    def _get_table(self, project_id: str, dataset_id: str, table_id: str) -> Table:
        dataset_ref = client.dataset(dataset_id, project=project_id)
        view_ref = dataset_ref.table(table_id)
        return client.get_table(view_ref)

    @staticmethod
    def extract_table_references(query, is_legacy_sql):
        # Remove comments from query to avoid picking up tables from commented out SQL code
        view_query = re.sub(COMMENTS_PATTERN, "", query)
        table_pattern = (
            LEGACY_SQL_TABLE_PATTERN if is_legacy_sql else STANDARD_SQL_TABLE_PATTERN
        )
        tables = re.findall(table_pattern, view_query, re.IGNORECASE | re.MULTILINE)
        return tables

    def _build_tree(self, table_node: TableNode) -> TableNode:
        table = table_node.table
        log.info(f"{table_node.name}")
        log.info(f"{table_node.name}: object is of type {table.table_type}")
        if table.table_type == "VIEW":
            tables = self.extract_table_references(
                table.view_query, table.view_use_legacy_sql
            )
            log.info(
                f"{table_node.name}: found {len(tables)} related object references in view DDL"
            )
            for i, t in enumerate(tables):
                project_id, dataset_id, table_id = t
                project_id = (
                    project_id or table.project
                )  # default to parent view's project
                child_table = self._get_table(project_id, dataset_id, table_id)
                child_node = TableNode(table=child_table, parent=table_node)
                log.info(
                    f"{table_node.name}: analyzing dependency tree for '{child_node.name}' ({i+1}/{len(tables)})"
                )
                self._build_tree(child_node)
        return table_node
