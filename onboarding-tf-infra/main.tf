terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "target_projects" {
  type        = list(string)
  description = "List of project IDs to create the role and binding in"
  default     = ["kora-498304", "saas-net-env"]
}

variable "role_id" {
  type        = string
  description = "ID for the custom role (no spaces/special chars)"
  default     = "tunerScopedRole"
}

variable "role_title" {
  type        = string
  description = "Display title for the custom role"
  default     = "Tuner Scoped Access"
}

variable "role_permissions" {
  type        = list(string)
  description = "Permissions included in the custom role"
  default = [
    "compute.instances.get",
    "compute.instances.list",
  ]
}

variable "service_account_member" {
  type        = string
  description = "Member string for the service account to bind the role to"
  default     = "serviceAccount:cktuner-service-account@ck-tuner-manage-sa.iam.gserviceaccount.com"
}

# --- Custom role, created independently in each target project ---
resource "google_project_iam_custom_role" "tuner_role" {
  for_each = toset(var.target_projects)

  project     = each.value
  role_id     = var.role_id
  title       = var.role_title
  permissions = var.role_permissions
}

# --- Bind the role to the service account, in each target project ---
resource "google_project_iam_member" "tuner_binding" {
  for_each = toset(var.target_projects)

  project = each.value
  role    = google_project_iam_custom_role.tuner_role[each.value].id
  member  = var.service_account_member
}

output "created_roles" {
  value = { for p, r in google_project_iam_custom_role.tuner_role : p => r.id }
}
