variable "config" {
  type = object({
    project = string
    location = string
    owner_email = string
  })
}

variable "commit_hash" {
  type = string
}
