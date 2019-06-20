# BigQuery View Analyzer
[![PyPI version](https://img.shields.io/pypi/v/bigquery-view-analyzer.svg)](https://pypi.python.org/pypi/bigquery-view-analyzer)
[![Python versions](https://img.shields.io/pypi/pyversions/bigquery-view-analyzer.svg)](https://pypi.python.org/pypi/bigquery-view-analyzer)
[![Build status](https://img.shields.io/travis/servian/bigquery-view-analyzer.svg)](https://travis-ci.org/servian/bigquery-view-analyzer)
[![Github license](https://img.shields.io/github/license/servian/bigquery-view-analyzer.svg)](https://github.com/servian/bigquery-view-analyzer)

## Description
`bigquery-view-analyzer` is a command-line tool for visualizing dependencies and managing permissions between BigQuery views.

To authorize a view, permissions must be granted at a dataset level for every view/table referenced in the view definition. This requirement cascades down to every view that's referenced by the parent view, they too must have permissions granted for every view/table they reference - and so on. This can quickly become difficult to manage if you have many nested views across multiple datasets and/or projects.

`bigquery-view-analyzer` automatically resolves these dependencies and applies the relevant permissions to all views and datasets referenced by the parent view.


## Installation

```bash
$ pip install bigquery-view-analyzer
```

## Usage

```bash
$ bqva --help
```

[![asciicast](https://asciinema.org/a/252724.svg)](https://asciinema.org/a/252724)


### Example

![Example tree](/docs/example.png)

Given the above datasets and tables in BigQuery, to authorize `bqva-demo:dataset_4.shared_view`, the following views would need to be authorized with each of the following datasets:

- Authorized views for **`dataset_1`**
    - `bqva-demo:dataset_3.view_a_b_c_d`
- Authorized views for **`dataset_2`**
    - `bqva-demo:dataset_3.view_a_b_c_d`
    - `bqva-demo:dataset_1.view_c`
- Authorized views for **`dataset_3`**
    - `bqva-demo:dataset_2.view_d`
    - `bqva-demo:dataset_4.shared_view`

You can easily visualize the above view hierarchy using the `bqva tree` command.

```bash
# View dependency tree and authorization status for 'bqva-demo:dataset_4.shared_view'
$ bqva tree --status --no-key --view "bqva-demo:dataset_4.shared_view"
bqva-demo:dataset_4.shared_view
└── bqva-demo:dataset_3.view_a_b_c_d (⨯)
    ├── bqva-demo:dataset_1.table_a (⨯)
    ├── bqva-demo:dataset_1.table_b (⨯)
    ├── bqva-demo:dataset_1.view_c (⨯)
    │   └── bqva-demo:dataset_2.table_c (⨯)
    └── bqva-demo:dataset_2.view_d (⨯)
        └── bqva-demo:dataset_3.table_d (⨯)
```

Permissions can be applied automatically to all datasets referenced by the parent view using the `bqva authorize` command.

```bash
# Apply all permissions required by 'bqva-demo:dataset_4.shared_view'
$ bqva authorize --view "bqva-demo:dataset_4.shared_view"
bqva-demo:dataset_4.shared_view
└── bqva-demo:dataset_3.view_a_b_c_d (✓)
    ├── bqva-demo:dataset_1.table_a (✓)
    ├── bqva-demo:dataset_1.table_b (✓)
    ├── bqva-demo:dataset_1.view_c (✓)
    │   └── bqva-demo:dataset_2.table_c (✓)
    └── bqva-demo:dataset_2.view_d (✓)
        └── bqva-demo:dataset_3.table_d (✓)
```

If you want to revoke permissions for a view, you can do that too!

```bash
# Revoke all permissions granted to 'bqva-demo:dataset_4.shared_view'
$ bqva revoke --view "bqva-demo:dataset_4.shared_view"
bqva-demo:dataset_4.shared_view
└── bqva-demo:dataset_3.view_a_b_c_d (⨯)
    ├── bqva-demo:dataset_1.table_a (⨯)
    ├── bqva-demo:dataset_1.table_b (⨯)
    ├── bqva-demo:dataset_1.view_c (⨯)
    │   └── bqva-demo:dataset_2.table_c (⨯)
    └── bqva-demo:dataset_2.view_d (⨯)
        └── bqva-demo:dataset_3.table_d (⨯)
```
