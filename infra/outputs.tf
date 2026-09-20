output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.relay_postgres.fqdn
  description = "PostgreSQL Flexible Server FQDN"
}

output "redis_hostname" {
  value       = azurerm_redis_cache.relay_redis.hostname
  description = "Azure Managed Redis Hostname"
}

output "storage_account_name" {
  value       = azurerm_storage_account.relay_storage.name
  description = "Audit Blob Storage Account Name"
}
