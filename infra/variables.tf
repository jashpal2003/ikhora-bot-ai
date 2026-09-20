variable "environment" {
  type        = string
  description = "Target deployment environment (dev, staging, prod)"
  default     = "dev"
}

variable "azure_region" {
  type        = string
  description = "Target Azure primary region"
  default     = "westeurope"
}

variable "db_admin_user" {
  type        = string
  description = "PostgreSQL administrator login"
  default     = "relay_admin"
}

variable "db_admin_password" {
  type        = string
  description = "PostgreSQL administrator password"
  sensitive   = true
}
