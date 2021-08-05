import logging

from anytree import RenderTree
from colorama import Fore, init

from .analyzer import TableNode, ViewAnalyzer

log = logging.getLogger("bqva.analyzer")

init(autoreset=True)


def color(color: str, text: str) -> str:
    return color + text + Fore.RESET


def format_key() -> str:
    return f"""
Key:
{color(Fore.CYAN, '◉')} Project
{color(Fore.YELLOW, '◉')} Dataset
{color(Fore.RED, '◉')} Table
{color(Fore.GREEN, '◉')} View
"""


def format_tree(tree: ViewAnalyzer, show_key=False, show_status=False):
    log.info("Formatting tree...")
    output = list()
    if show_key:
        output.append(format_key())
    for pre, _, node in RenderTree(tree):
        output.append(pre + format_node(node, show_status=show_status))
    return "\n".join(output)


def format_node(node: TableNode, show_status=False) -> str:
    project = color(Fore.CYAN, node.project)
    dataset = color(Fore.YELLOW, node.dataset_id)
    if node.table.table_type == "VIEW":
        table = color(Fore.GREEN, node.table_id)
    else:
        table = color(Fore.RED, node.table_id)
    name = f"{project}:{dataset}.{table}"

    if show_status:
        if node.is_authorized():
            status = color(Fore.GREEN, "✓")
        else:
            status = color(Fore.RED, "⨯")
        name += " " + status
    return name
