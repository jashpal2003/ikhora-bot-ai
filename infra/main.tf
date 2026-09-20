# =============================================================================
# Project Relay — Infrastructure as Code (Terraform for Azure)
# Provisions: Azure Container Apps, PostgreSQL Flexible Server (pgvector),
# Azure Managed Redis, Azure Blob Storage (Immutable Audit), Key Vault, Front Door
# =============================================================================

terraform {
  required_version = ">= 1.8.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.116.0"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

resource "azurerm_resource_group" "relay_rg" {
  name     = "rg-relay-${var.environment}"
  location = var.azure_region
}

# -----------------------------------------------------------------------------
# 1. Managed Identity & Key Vault
# -----------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "relay_identity" {
  name                = "id-relay-${var.environment}"
  resource_group_name = azurerm_resource_group.relay_rg.name
  location            = azurerm_resource_group.relay_rg.location
}

# -----------------------------------------------------------------------------
# 2. Azure Database for PostgreSQL Flexible Server (pgvector, RLS enabled)
# -----------------------------------------------------------------------------
resource "azurerm_postgresql_flexible_server" "relay_postgres" {
  name                   = "psql-relay-${var.environment}"
  resource_group_name    = azurerm_resource_group.relay_rg.name
  location               = azurerm_resource_group.relay_rg.location
  version                = "16"
  administrator_login    = var.db_admin_user
  administrator_password = var.db_admin_password
  zone                   = "1"
  storage_mb             = 65536
  sku_name               = "GP_Standard_D4ds_v5"
  backup_retention_days  = 35
  geo_redundant_backup_enabled = false
}

resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.relay_postgres.id
  value     = "VECTOR,UUID-OSSP,PGCRYPTO"
}

# -----------------------------------------------------------------------------
# 3. Azure Managed Redis (Ephemeral & Hot Caches)
# -----------------------------------------------------------------------------
resource "azurerm_redis_cache" "relay_redis" {
  name                = "redis-relay-${var.environment}"
  location            = azurerm_resource_group.relay_rg.location
  resource_group_name = azurerm_resource_group.relay_rg.name
  capacity            = 1
  family              = "C"
  sku_name            = "Standard"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
}

# -----------------------------------------------------------------------------
# 4. Azure Blob Storage (Immutable Audit Tier)
# -----------------------------------------------------------------------------
resource "azurerm_storage_account" "relay_storage" {
  name                     = "strelay${var.environment}"
  resource_group_name      = azurerm_resource_group.relay_rg.name
  location                 = azurerm_resource_group.relay_rg.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
}

resource "azurerm_storage_container" "audit_container" {
  name                  = "audit-events"
  storage_account_name  = azurerm_storage_account.relay_storage.name
  container_access_type = "private"
}

# -----------------------------------------------------------------------------
# 5. Azure Container Apps Environment & Deployables
# -----------------------------------------------------------------------------
resource "azurerm_container_app_environment" "relay_env" {
  name                = "cae-relay-${var.environment}"
  location            = azurerm_resource_group.relay_rg.location
  resource_group_name = azurerm_resource_group.relay_rg.name
}
