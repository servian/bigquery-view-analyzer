import logging
import os
import re

import click
from anytree.exporter import DotExporter
from yaspin import yaspin

from . import utils
from .analyzer import ViewAnalyzer

log = logging.getLogger()


TABLE_PATTERN = (
    r"^(?:(?P<project>[^\:\.]+?)(?:\:))?(?P<dataset>[^\:\.]+?)\.(?P<table>[^\:\.]+?)$"
)
VIEW_HELP_TEXT = (
    "Name of the view in the format [PROJECT]:[DATASET].[VIEW] or [DATASET].[VIEW]."
)


class ViewParameter(click.ParamType):
    name = "View"

    def convert(self, value, param, ctx):
        m = re.search(TABLE_PATTERN, value)
        if m:
            project, dataset, view = m.groups()
            return ViewAnalyzer(project_id=project, dataset_id=dataset, view_id=view)
        else:
            self.fail(
                "View must be in the format [PROJECT]:[DATASET].[VIEW] or [DATASET].[VIEW]."
            )


@click.group()
@click.option("--debug/--no-debug", default=False)
def main(debug):
    """BigQuery View Analyzer

    A command-line tool for visualizing dependencies and managing permissions between BigQuery views.
    """
    if debug:
        handler = logging.FileHandler(os.path.join(os.getcwd(), "debug.log"))
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)
    else:
        handler = logging.NullHandler()
        log.addHandler(logging.NullHandler())
        log.setLevel(logging.NOTSET)


@main.command()
@click.option("--view", "-v", type=ViewParameter(), help=VIEW_HELP_TEXT)
def authorize(view):
    with yaspin(
        text="Applying nested authorized view permissions for view '{}'".format(view),
        color="yellow",
    ):
        view.apply_permissions()
        formatted_tree = utils.format_tree(view, show_status=True)
    print(formatted_tree)


@main.command()
@click.option("--view", "-v", type=ViewParameter(), help=VIEW_HELP_TEXT)
def revoke(view):
    with yaspin(
        text="Revoking nested authorized view permissions for view '{}'".format(view),
        color="yellow",
    ):
        view.revoke_permissions()
        formatted_tree = utils.format_tree(view, show_status=True)
    print(formatted_tree)


@main.command()
@click.option("--view", "-v", type=ViewParameter(), help=VIEW_HELP_TEXT)
@click.option("--status/--no-status", default=False, help="Show authorization status.")
@click.option("--key/--no-key", default=True, help="Show color key.")
def tree(view, status, key):
    with yaspin(
        text="Fetching dependency tree for view '{}'".format(view), color="yellow"
    ):
        formatted_tree = utils.format_tree(view, show_status=status, show_key=key)
    print(formatted_tree)


@main.command()
@click.option("--view", "-v", type=ViewParameter(), help=VIEW_HELP_TEXT)
@click.option(
    "--filename", "-f", type=click.Path(exists=False, file_okay=True, dir_okay=False)
)
def image(view, filename):
    """
    Export an image representation of a view's dependency tree.

    Requires the 'graphviz' package to be installed.
    """
    with yaspin(
        text="Exporting dependency tree image for view '{}'".format(view),
        color="yellow",
    ):
        DotExporter(view.tree).to_picture(filename)
    click.echo("Image saved to: {}".format(filename))


if __name__ == "__main__":
    main()
