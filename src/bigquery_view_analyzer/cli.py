import click
import re

from yaspin import yaspin
from bigquery_view_analyzer import ViewAnalyzer


TABLE_PATTERN = r"^(?:(?P<project>.+?)(?:\:))?(?P<dataset>.+?)\.(?P<table>.+?)$"


def get_view_analyzer(view):
    m = re.search(TABLE_PATTERN, view)
    if m:
        project, dataset, view = m.groups()
        return ViewAnalyzer(project_id=project, dataset_id=dataset, view_id=view)
    click.echo("View must be in the format [PROJECT]:[DATASET].[VIEW]")
    return None


@click.group()
def main():
    pass


@main.command()
@click.argument("view")
def authorize(view):
    with yaspin(
        text="Applying nested authorized view permissions for view '{}'".format(view),
        color="yellow",
    ) as sp:
        va = get_view_analyzer(view)
        if not va:
            return
        va.apply_permissions()
        formatted_tree = va.format_tree(show_status=True)
        sp.hide()
        print(formatted_tree)


@main.command()
@click.argument("view")
def revoke(view):
    with yaspin(
        text="Revoking nested authorized view permissions for view '{}'".format(view),
        color="yellow",
    ) as sp:
        va = get_view_analyzer(view)
        if not va:
            return
        va.revoke_permissions()
        formatted_tree = va.format_tree(show_status=True)
        sp.hide()
        print(formatted_tree)


@main.command()
@click.argument("view")
def tree(view):
    with yaspin(
        text="Fetching dependency tree for view '{}'".format(view), color="yellow"
    ) as sp:
        va = get_view_analyzer(view)
        if not va:
            return
        formatted_tree = va.format_tree(show_status=False)
        sp.hide()
        print(formatted_tree)


if __name__ == "__main__":
    main()
