# Table Definitions, DSL Queries & DAO Pattern

## Table Definitions

### DSL Style Tables

```kotlin
// tables/UsersTable.kt
object UsersTable : UUIDTable("users") {
    val name = varchar("name", 100)
    val email = varchar("email", 255).uniqueIndex()
    val role = enumerationByName<Role>("role", 20)
    val metadata = jsonb<UserMetadata>("metadata", Json.Default).nullable()
    val createdAt = timestampWithTimeZone("created_at").defaultExpression(CurrentTimestampWithTimeZone)
    val updatedAt = timestampWithTimeZone("updated_at").defaultExpression(CurrentTimestampWithTimeZone)
}

object OrdersTable : UUIDTable("orders") {
    val userId = uuid("user_id").references(UsersTable.id)
    val status = enumerationByName<OrderStatus>("status", 20)
    val totalAmount = long("total_amount")
    val currency = varchar("currency", 3)
    val createdAt = timestampWithTimeZone("created_at").defaultExpression(CurrentTimestampWithTimeZone)
}

object OrderItemsTable : UUIDTable("order_items") {
    val orderId = uuid("order_id").references(OrdersTable.id, onDelete = ReferenceOption.CASCADE)
    val productId = uuid("product_id")
    val quantity = integer("quantity")
    val unitPrice = long("unit_price")
}
```

### Composite Tables

```kotlin
object UserRolesTable : Table("user_roles") {
    val userId = uuid("user_id").references(UsersTable.id, onDelete = ReferenceOption.CASCADE)
    val roleId = uuid("role_id").references(RolesTable.id, onDelete = ReferenceOption.CASCADE)
    override val primaryKey = PrimaryKey(userId, roleId)
}
```

## DSL Queries

### Basic CRUD

```kotlin
// Insert
suspend fun insertUser(name: String, email: String, role: Role): UUID =
    newSuspendedTransaction {
        UsersTable.insertAndGetId {
            it[UsersTable.name] = name
            it[UsersTable.email] = email
            it[UsersTable.role] = role
        }.value
    }

// Select by ID
suspend fun findUserById(id: UUID): UserRow? =
    newSuspendedTransaction {
        UsersTable.selectAll()
            .where { UsersTable.id eq id }
            .map { it.toUser() }
            .singleOrNull()
    }

// Select with conditions
suspend fun findActiveAdmins(): List<UserRow> =
    newSuspendedTransaction {
        UsersTable.selectAll()
            .where { (UsersTable.role eq Role.ADMIN) }
            .orderBy(UsersTable.name)
            .map { it.toUser() }
    }

// Update
suspend fun updateUserEmail(id: UUID, newEmail: String): Boolean =
    newSuspendedTransaction {
        UsersTable.update({ UsersTable.id eq id }) {
            it[email] = newEmail
            it[updatedAt] = CurrentTimestampWithTimeZone
        } > 0
    }

// Delete
suspend fun deleteUser(id: UUID): Boolean =
    newSuspendedTransaction {
        UsersTable.deleteWhere { UsersTable.id eq id } > 0
    }

// Row mapping
private fun ResultRow.toUser() = UserRow(
    id = this[UsersTable.id].value,
    name = this[UsersTable.name],
    email = this[UsersTable.email],
    role = this[UsersTable.role],
    metadata = this[UsersTable.metadata],
    createdAt = this[UsersTable.createdAt],
    updatedAt = this[UsersTable.updatedAt],
)
```

### Advanced Queries

```kotlin
// Join queries
suspend fun findOrdersWithUser(userId: UUID): List<OrderWithUser> =
    newSuspendedTransaction {
        (OrdersTable innerJoin UsersTable)
            .selectAll()
            .where { OrdersTable.userId eq userId }
            .orderBy(OrdersTable.createdAt, SortOrder.DESC)
            .map { row ->
                OrderWithUser(
                    orderId = row[OrdersTable.id].value,
                    status = row[OrdersTable.status],
                    totalAmount = row[OrdersTable.totalAmount],
                    userName = row[UsersTable.name],
                )
            }
    }

// Aggregation
suspend fun countUsersByRole(): Map<Role, Long> =
    newSuspendedTransaction {
        UsersTable
            .select(UsersTable.role, UsersTable.id.count())
            .groupBy(UsersTable.role)
            .associate { row ->
                row[UsersTable.role] to row[UsersTable.id.count()]
            }
    }

// Subqueries
suspend fun findUsersWithOrders(): List<UserRow> =
    newSuspendedTransaction {
        UsersTable.selectAll()
            .where {
                UsersTable.id inSubQuery
                    OrdersTable.select(OrdersTable.userId).withDistinct()
            }
            .map { it.toUser() }
    }

// LIKE and pattern matching — always escape user input to prevent wildcard injection
private fun escapeLikePattern(input: String): String =
    input.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

suspend fun searchUsers(query: String): List<UserRow> =
    newSuspendedTransaction {
        val sanitized = escapeLikePattern(query.lowercase())
        UsersTable.selectAll()
            .where {
                (UsersTable.name.lowerCase() like "%${sanitized}%") or
                    (UsersTable.email.lowerCase() like "%${sanitized}%")
            }
            .map { it.toUser() }
    }
```

### Pagination

```kotlin
data class Page<T>(
    val data: List<T>,
    val total: Long,
    val page: Int,
    val limit: Int,
) {
    val totalPages: Int get() = ((total + limit - 1) / limit).toInt()
    val hasNext: Boolean get() = page < totalPages
    val hasPrevious: Boolean get() = page > 1
}

suspend fun findUsersPaginated(page: Int, limit: Int): Page<UserRow> =
    newSuspendedTransaction {
        val total = UsersTable.selectAll().count()
        val data = UsersTable.selectAll()
            .orderBy(UsersTable.createdAt, SortOrder.DESC)
            .limit(limit)
            .offset(((page - 1) * limit).toLong())
            .map { it.toUser() }

        Page(data = data, total = total, page = page, limit = limit)
    }
```

### Batch Operations

```kotlin
// Batch insert
suspend fun insertUsers(users: List<CreateUserRequest>): List<UUID> =
    newSuspendedTransaction {
        UsersTable.batchInsert(users) { user ->
            this[UsersTable.name] = user.name
            this[UsersTable.email] = user.email
            this[UsersTable.role] = user.role
        }.map { it[UsersTable.id].value }
    }

// Upsert (insert or update on conflict)
suspend fun upsertUser(id: UUID, name: String, email: String) {
    newSuspendedTransaction {
        UsersTable.upsert(UsersTable.email) {
            it[UsersTable.id] = EntityID(id, UsersTable)
            it[UsersTable.name] = name
            it[UsersTable.email] = email
            it[updatedAt] = CurrentTimestampWithTimeZone
        }
    }
}
```

## DAO Pattern

### Entity Definitions

```kotlin
// entities/UserEntity.kt
class UserEntity(id: EntityID<UUID>) : UUIDEntity(id) {
    companion object : UUIDEntityClass<UserEntity>(UsersTable)

    var name by UsersTable.name
    var email by UsersTable.email
    var role by UsersTable.role
    var metadata by UsersTable.metadata
    var createdAt by UsersTable.createdAt
    var updatedAt by UsersTable.updatedAt

    val orders by OrderEntity referrersOn OrdersTable.userId

    fun toModel(): User = User(
        id = id.value,
        name = name,
        email = email,
        role = role,
        metadata = metadata,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )
}

class OrderEntity(id: EntityID<UUID>) : UUIDEntity(id) {
    companion object : UUIDEntityClass<OrderEntity>(OrdersTable)

    var user by UserEntity referencedOn OrdersTable.userId
    var status by OrdersTable.status
    var totalAmount by OrdersTable.totalAmount
    var currency by OrdersTable.currency
    var createdAt by OrdersTable.createdAt

    val items by OrderItemEntity referrersOn OrderItemsTable.orderId
}
```

### DAO Operations

```kotlin
suspend fun findUserByEmail(email: String): User? =
    newSuspendedTransaction {
        UserEntity.find { UsersTable.email eq email }
            .firstOrNull()
            ?.toModel()
    }

suspend fun createUser(request: CreateUserRequest): User =
    newSuspendedTransaction {
        UserEntity.new {
            name = request.name
            email = request.email
            role = request.role
        }.toModel()
    }

suspend fun updateUser(id: UUID, request: UpdateUserRequest): User? =
    newSuspendedTransaction {
        UserEntity.findById(id)?.apply {
            request.name?.let { name = it }
            request.email?.let { email = it }
            updatedAt = OffsetDateTime.now(ZoneOffset.UTC)
        }?.toModel()
    }
```
