provider "google" { project = var.config.project }
data "google_client_openid_userinfo" "me" {}
resource "time_static" "timestamp" {}

locals {
  dataset_description = "Created automatically as part of BQVA's integration test suite."
  table_ddl = "SELECT %s AS row, '%s' AS dataset, '%s' AS table, '%s' AS commit"

  datasets = ["a", "b", "c"]
  tables = {
    for t in setproduct(local.datasets, range(1, 3)) : "table_${t[0]}${t[1]}" => t[0]
  }
  views = {
    dataset_a = [
      { ref = "table_a1" }
    ]
  }
}

resource "google_bigquery_dataset" "dataset" {
  for_each = toset(local.datasets)

  dataset_id                  = upper("dataset_${each.key}")
  friendly_name               = "BQVA: Dataset ${upper(each.key)}"
  description                 = local.dataset_description
  location                    = var.config.location
  default_table_expiration_ms = 3600000
  delete_contents_on_destroy = true

  labels = {
    commit = var.commit_hash
  }

  access {
    role          = "OWNER"
    user_by_email = var.config.owner_email
  }

  access {
    role          = "WRITER"
    user_by_email = data.google_client_openid_userinfo.me.email
  }

  access {
    role   = "READER"
    special_group = "allAuthenticatedUsers"
  }
}

resource "google_bigquery_table" "table" {
  for_each = local.tables

  dataset_id = google_bigquery_dataset.dataset[each.value].dataset_id
  table_id   = upper(each.key)
  deletion_protection = false

  labels = {
    commit = var.commit_hash
  }

  schema = <<EOF
[
  {
    "name": "row",
    "type": "INTEGER",
    "mode": "REQUIRED"
  },
  {
    "name": "dataset",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "table",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "commit",
    "type": "STRING",
    "mode": "NULLABLE"
  }
]
EOF

}


resource "google_bigquery_job" "job" {
  for_each = google_bigquery_table.table

  location = var.config.location
  job_id     = format("%s_%s", each.value.table_id, formatdate("YYYYMMDDhhmmss", timestamp()))

  labels = {
    commit = var.commit_hash
  }

  query {
    query = join(
      "\nUNION ALL\n",
      [ for i in range(1, 11) : format(local.table_ddl, i, each.value.dataset_id, each.value.table_id, var.commit_hash) ]
    )
    write_disposition = "WRITE_TRUNCATE"

    destination_table {
      table_id = each.value.id
    }
  }

  depends_on = [google_bigquery_dataset.dataset, google_bigquery_table.table]
}
