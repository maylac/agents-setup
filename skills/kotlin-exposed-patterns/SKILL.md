---
name: kotlin-exposed-patterns
description: Use when setting up or querying JetBrains Exposed ORM — transactions, HikariCP, Flyway, DSL vs DAO choice, repository pattern. Not for generic SQL questions.
origin: ECC
---

# Kotlin Exposed Patterns

Comprehensive patterns for database access with JetBrains Exposed ORM, including DSL queries, DAO, transactions, and production-ready configuration.

## When to Use

- Setting up database access with Exposed
- Writing SQL queries using Exposed DSL or DAO
- Configuring connection pooling with HikariCP
- Creating database migrations with Flyway
- Implementing the repository pattern with Exposed
- Handling JSON columns and complex queries

## How It Works

Exposed provides two query styles: DSL for direct SQL-like expressions and DAO for entity lifecycle management. HikariCP manages a pool of reusable database connections configured via `HikariConfig`. Flyway runs versioned SQL migration scripts at startup to keep the schema in sync. All database operations run inside `newSuspendedTransaction` blocks for coroutine safety and atomicity. The repository pattern wraps Exposed queries behind an interface so business logic stays decoupled from the data layer and tests can use an in-memory H2 database.

## Examples

### DSL Query

```kotlin
suspend fun findUserById(id: UUID): UserRow? =
    newSuspendedTransaction {
        UsersTable.selectAll()
            .where { UsersTable.id eq id }
            .map { it.toUser() }
            .singleOrNull()
    }
```

### DAO Entity Usage

```kotlin
suspend fun createUser(request: CreateUserRequest): User =
    newSuspendedTransaction {
        UserEntity.new {
            name = request.name
            email = request.email
            role = request.role
        }.toModel()
    }
```

### HikariCP Configuration

```kotlin
val hikariConfig = HikariConfig().apply {
    driverClassName = config.driver
    jdbcUrl = config.url
    username = config.username
    password = config.password
    maximumPoolSize = config.maxPoolSize
    isAutoCommit = false
    transactionIsolation = "TRANSACTION_READ_COMMITTED"
    validate()
}
```

## Database Setup

### HikariCP Connection Pooling

```kotlin
// DatabaseFactory.kt
object DatabaseFactory {
    fun create(config: DatabaseConfig): Database {
        val hikariConfig = HikariConfig().apply {
            driverClassName = config.driver
            jdbcUrl = config.url
            username = config.username
            password = config.password
            maximumPoolSize = config.maxPoolSize
            isAutoCommit = false
            transactionIsolation = "TRANSACTION_READ_COMMITTED"
            validate()
        }

        return Database.connect(HikariDataSource(hikariConfig))
    }
}

data class DatabaseConfig(
    val url: String,
    val driver: String = "org.postgresql.Driver",
    val username: String = "",
    val password: String = "",
    val maxPoolSize: Int = 10,
)
```

### Flyway Migrations

```kotlin
// FlywayMigration.kt
fun runMigrations(config: DatabaseConfig) {
    Flyway.configure()
        .dataSource(config.url, config.username, config.password)
        .locations("classpath:db/migration")
        .baselineOnMigrate(true)
        .load()
        .migrate()
}

// Application startup
fun Application.module() {
    val config = DatabaseConfig(
        url = environment.config.property("database.url").getString(),
        username = environment.config.property("database.username").getString(),
        password = environment.config.property("database.password").getString(),
    )
    runMigrations(config)
    val database = DatabaseFactory.create(config)
    // ...
}
```

### Migration Files

```sql
-- src/main/resources/db/migration/V1__create_users.sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(20) NOT NULL DEFAULT 'USER',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

## Table Definitions, DSL Queries & DAO Pattern

Table/object definitions, DSL query patterns, and the DAO pattern are in [references/queries-and-dao.md](references/queries-and-dao.md).

## Transactions

### Suspend Transaction Support

```kotlin
// Good: Use newSuspendedTransaction for coroutine support
suspend fun performDatabaseOperation(): Result<User> =
    runCatching {
        newSuspendedTransaction {
            val user = UserEntity.new {
                name = "Alice"
                email = "alice@example.com"
            }
            // All operations in this block are atomic
            user.toModel()
        }
    }

// Good: Nested transactions with savepoints
suspend fun transferFunds(fromId: UUID, toId: UUID, amount: Long) {
    newSuspendedTransaction {
        val from = UserEntity.findById(fromId) ?: throw NotFoundException("User $fromId not found")
        val to = UserEntity.findById(toId) ?: throw NotFoundException("User $toId not found")

        // Debit
        from.balance -= amount
        // Credit
        to.balance += amount

        // Both succeed or both fail
    }
}
```

### Transaction Isolation

```kotlin
suspend fun readCommittedQuery(): List<User> =
    newSuspendedTransaction(transactionIsolation = Connection.TRANSACTION_READ_COMMITTED) {
        UserEntity.all().map { it.toModel() }
    }

suspend fun serializableOperation() {
    newSuspendedTransaction(transactionIsolation = Connection.TRANSACTION_SERIALIZABLE) {
        // Strictest isolation level for critical operations
    }
}
```

## Repository Pattern, JSON Columns & Testing

Repository pattern, JSON column mapping, and testing-with-Exposed patterns are in [references/advanced.md](references/advanced.md).

## Gradle Dependencies

```kotlin
// build.gradle.kts
dependencies {
    // Exposed
    implementation("org.jetbrains.exposed:exposed-core:1.0.0")
    implementation("org.jetbrains.exposed:exposed-dao:1.0.0")
    implementation("org.jetbrains.exposed:exposed-jdbc:1.0.0")
    implementation("org.jetbrains.exposed:exposed-kotlin-datetime:1.0.0")
    implementation("org.jetbrains.exposed:exposed-json:1.0.0")

    // Database driver
    implementation("org.postgresql:postgresql:42.7.5")

    // Connection pooling
    implementation("com.zaxxer:HikariCP:6.2.1")

    // Migrations
    implementation("org.flywaydb:flyway-core:10.22.0")
    implementation("org.flywaydb:flyway-database-postgresql:10.22.0")

    // Testing
    testImplementation("com.h2database:h2:2.3.232")
}
```

## Quick Reference: Exposed Patterns

| Pattern | Description |
|---------|-------------|
| `object Table : UUIDTable("name")` | Define table with UUID primary key |
| `newSuspendedTransaction { }` | Coroutine-safe transaction block |
| `Table.selectAll().where { }` | Query with conditions |
| `Table.insertAndGetId { }` | Insert and return generated ID |
| `Table.update({ condition }) { }` | Update matching rows |
| `Table.deleteWhere { }` | Delete matching rows |
| `Table.batchInsert(items) { }` | Efficient bulk insert |
| `innerJoin` / `leftJoin` | Join tables |
| `orderBy` / `limit` / `offset` | Sort and paginate |
| `count()` / `sum()` / `avg()` | Aggregation functions |

**Remember**: Use the DSL style for simple queries and the DAO style when you need entity lifecycle management. Always use `newSuspendedTransaction` for coroutine support, and wrap database operations behind a repository interface for testability.
