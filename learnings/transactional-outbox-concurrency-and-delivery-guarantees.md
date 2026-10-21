# Transactional Outbox: Concurrency, Delivery Guarantees, and Recovery

**Architecture decision and engineering case study**  
**Context:** Python 3.14 Bookstore REST API (hypothetical future capability)  
**Decision:** MySQL-backed outbox claiming with short transactions, expiring leases, publisher confirms, and idempotent consumers  
**Status:** Proposed; **not implemented**

## Executive summary

A transactional outbox solves one specific problem: persisting a business change and the *intent to publish an event* atomically in one database transaction. It does **not** make publication to RabbitMQ exactly-once. Concurrent workers, crashes, timeouts, and lost publisher confirmations can still produce duplicate messages.

For the Bookstore API, prefer the smallest maintainable design:

1. Write the business state and an outbox event in the same MySQL transaction.
2. Have workers claim separate batches using `SELECT ... FOR UPDATE SKIP LOCKED` and an expiring lease in MySQL.
3. Commit the claim before contacting RabbitMQ; never hold database row locks across broker I/O.
4. Publish with RabbitMQ publisher confirms and appropriate durability/routing configuration.
5. Mark an event published only when the current lease token still matches.
6. Treat delivery as **at least once** and make consumers idempotent.
7. For non-idempotent external effects (such as shipping), reconcile ambiguous outcomes; do not blindly retry.

**Scope note:** The current tutorial has not implemented `Book.reserve()`, `Order`, `OrderRepository`, `DomainEvent`, a transactional outbox, or a fulfillment service. These are hypothetical components in an advanced architecture exercise, not existing files or functionality.

## The original Staff/Principal-level question

An order-creation use case writes an order, reserves inventory, and stores an `OrderCreated` event in a transactional outbox. Two publishers concurrently select the same unpublished event, `E-100`:

| Step | Worker A | Worker B |
|---|---|---|
| 1 | Reads `E-100` | Reads `E-100` |
| 2 | Publishes to RabbitMQ | Publishes the same event |
| 3 | Receives publisher confirm | Receives publisher confirm |
| 4 | Crashes before marking published | Marks published |
| 5 | Restarts | Continues |

A fulfillment consumer then invokes a shipping provider that **does not support idempotency keys**, but permits lookup by merchant reference; that lookup may be eventually consistent.

**Design challenge:** Prevent avoidable concurrent publishing; recover from crashes; state achievable delivery guarantees; prevent duplicated business effects where possible; define what happens when shipment creation succeeded but the response or local persistence was lost. Assign each responsibility to the appropriate layer without excessive abstractions.

## 1. Invariants and guarantees

| Concern | Realistic guarantee | Not guaranteed |
|---|---|---|
| Order + outbox insertion | Atomic commit in one MySQL transaction | Atomic commit with RabbitMQ |
| Worker claiming | Usually one valid owner of a claim at a time | No concurrent publication if leases expire |
| RabbitMQ publication | At-least-once attempts with retries, when infrastructure and workers recover | Exactly-once delivery |
| Database-only consumer effects | Once-per-event committed effect with transactional deduplication | Exactly-once message receipt |
| External shipping API without idempotent create | Controlled retries and eventual reconciliation when provider data becomes conclusive | Strictly exactly-once shipment creation in all failures |

Publisher confirms indicate broker acceptance according to the broker's configuration and confirm semantics; they are **not** a durable receipt that another worker can independently query by confirmation tag. RabbitMQ delivery tags and publisher confirm sequence numbers are channel-scoped.

## 2. Alternatives considered

### A. Redis leases with TTL

**Approach:** `SET outbox:lease:E-100 <unique-owner-token> NX EX 30`; publishers coordinate through Redis. Release by atomic compare-and-delete, never unconditional deletion.

**Advantages:** Fast atomic key operations, TTL recovery, convenient when Redis is already a necessary coordination layer.

**Drawbacks:** Introduces a second state system alongside MySQL; Redis failover/expiration and MySQL state can disagree. Lease expiry can produce concurrent publishers. A Redis field recording a RabbitMQ confirm does not close the crash window between broker acceptance and recording confirmation. More components to operate for no stronger exactly-once guarantee.

**Decision:** Reject as a default for this MySQL-backed outbox.

### B. Hold `SELECT ... FOR UPDATE` locks throughout RabbitMQ publication

**Approach:** Lock an outbox row, publish, await confirm, update status, then commit.

**Advantages:** Straightforward ownership while the transaction remains healthy; little lease bookkeeping.

**Drawbacks:** Database locks and transactions remain open across external network I/O; blocked workers, lock waits, connection consumption, and long-running transactions become operational hazards. A crash after broker acceptance but before DB commit still leads to republishing.

**Decision:** Reject: it couples MySQL transaction duration to RabbitMQ latency without solving duplicate publication.

### C. MySQL claim transaction + expiring lease **(chosen)**

**Approach:** In a short transaction, find eligible rows with `FOR UPDATE SKIP LOCKED`, assign lease tokens and deadlines, and commit. Publish outside the transaction. Conditionally mark published only if the token still matches.

**Advantages:** One durable coordination datastore; concurrent worker scaling; short locks; crash recovery; minimal new infrastructure.

**Drawbacks:** Requires lease lifecycle and monitoring; cannot prevent duplicate publication after a confirm/DB-update failure or expired claim; additional ordering rules are required for per-aggregate event order.

**Decision:** Adopt.

### D. Single publisher process

**Advantages:** Very simple initially, no concurrent claim contention.

**Drawbacks:** Limited throughput and availability, no guarantee against duplicates on restart. Could be acceptable for an early prototype, but not the target multi-worker design.

**Decision:** Viable stepping stone, not the long-term decision.

## 3. Chosen data model

Illustrative schema (not a migration to apply yet):

```sql
CREATE TABLE outbox_events (
    id BINARY(16) NOT NULL PRIMARY KEY,
    event_type VARCHAR(120) NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    lease_token BINARY(16) NULL,
    claimed_until DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    published_at DATETIME(6) NULL,
    INDEX idx_outbox_status_claim_created
        (status, claimed_until, created_at, id)
) ENGINE=InnoDB;
```

States: `PENDING` (eligible), `CLAIMED` (temporarily owned), `PUBLISHED` (confirmed and recorded locally). An expired `CLAIMED` row becomes **eligible** without needing an intermediate reset. Retain events long enough for operational review and consumers' deduplication needs.

For large tables or heavily loaded systems, test the actual query plan for the `OR` eligibility predicate; consider separate indexed selection passes or a purpose-built next-attempt timestamp if needed. The index above is an illustrative starting point, not a guarantee of an optimal plan.

## 4. Claim in a short transaction

```sql
START TRANSACTION;

SELECT id
FROM outbox_events
WHERE status = 'PENDING'
   OR (status = 'CLAIMED' AND claimed_until < UTC_TIMESTAMP(6))
ORDER BY created_at, id
LIMIT 20
FOR UPDATE SKIP LOCKED;

-- For each selected row, assign a NEW random lease_token and deadline:
UPDATE outbox_events
SET status = 'CLAIMED',
    lease_token = :new_lease_token,
    claimed_until = UTC_TIMESTAMP(6) + INTERVAL 30 SECOND
WHERE id = :id;

COMMIT;
```

This is an illustration of the algorithm, not a single copy/paste-ready prepared statement for multiple rows. Execute the updates inside the **same transaction** as the locking select. Use database UTC time consistently.

`SKIP LOCKED` is suitable for queue-like claims, even though it intentionally returns an inconsistent view of concurrently locked rows; do not use it as a general consistency mechanism for domain reads. Ordering of selection does **not** mean publication order is guaranteed.

**Lease duration:** `30 seconds` is only an example. Choose it based on observed publish latency, bounded broker timeouts, batch size, and worker behavior. Prefer sufficiently small processing units; if processing may exceed the lease, use carefully controlled renewals or a larger lease. A token protects database status from stale owners but does **not** prevent a stale owner from publishing.

## 5. Publish and finalize

Conceptual worker logic:

```python
claimed = outbox.claim_batch(limit=20)  # transaction commits before returning

for event in claimed:
    confirmed = publisher.publish_and_wait_for_confirm(event)
    if confirmed:
        updated = outbox.mark_published(
            event_id=event.id,
            lease_token=event.lease_token,
        )
        if not updated:
            # Lease was lost or another worker finished it.
            # Do not overwrite current ownership.
            report_stale_claim(event.id)
```

These APIs are **hypothetical**, not implemented; the code is not a tutorial file to add yet.

The conditional update is the key protection:

```sql
UPDATE outbox_events
SET status = 'PUBLISHED',
    published_at = UTC_TIMESTAMP(6),
    lease_token = NULL,
    claimed_until = NULL
WHERE id = :event_id
  AND status = 'CLAIMED'
  AND lease_token = :lease_token;
```

Require affected row count = 1 to claim success. After lease expiration, Worker B may replace the lease token; Worker A's late completion then updates zero rows. Using only `worker_id` is weaker because worker identifiers may be reused; a unique token per *claim* is sufficient for this database ownership check. Monotonic fencing tokens are useful when external systems can reject stale generations; RabbitMQ publication itself does not enforce the fencing token here.

**RabbitMQ settings:** Publisher confirms must be enabled; message and queue durability depend on appropriate exchange/queue configuration and persistent-message semantics. Use mandatory publishing and returned-message handling (or another suitable routing assurance mechanism) so an unroutable message is not treated as successfully delivered to an intended queue merely because a publisher confirm arrived. Confirmed publication still does not establish consumer processing.

## 6. Failure matrix

| Failure | Outcome | Recovery |
|---|---|---|
| Transaction creating order/outbox rolls back | Neither persists | Surface business/transaction failure; no event to publish |
| Worker crashes before claim commit | No durable claim | Another worker claims |
| Worker crashes after claim commit, before publish | Event remains `CLAIMED` | Recover when lease expires |
| RabbitMQ accepts event but confirm is lost | Publication outcome unknown | Retry after timeout/lease; potential duplicate |
| Confirm received, worker crashes before MySQL update | Event remains unpublished locally | Retry; potential duplicate |
| Lease expires while A publishes; B reclaims | Concurrent publication possible | Lease-token check blocks stale DB update; consumer deduplication |
| Worker marks event `PUBLISHED` with old token | Update affects zero rows | Do not overwrite newer claim; observe/report |
| RabbitMQ unreachable | Confirm unavailable | Retry when claim eligible; monitor backlog |
| Worker repeatedly fails on malformed event | Backlog/retries may repeat forever | Operational visibility; later add retry limits/quarantine |

There is no atomic transaction spanning RabbitMQ acceptance and the MySQL `PUBLISHED` update; therefore the outbox alone **cannot guarantee exactly-once delivery**.

## 7. Consumer design: idempotency where it is achievable

Carry an immutable event ID in every published message, separate from the order ID. A consumer using only its own database can make deduplication and database writes atomic:

1. Begin a DB transaction.
2. Insert a `(consumer_name, event_id)` record with a unique constraint; if it already exists, treat the event as previously processed.
3. Perform the consumer's local business writes.
4. Commit both the writes and deduplication record.
5. Acknowledge the RabbitMQ delivery **after** commit.

If the process crashes after commit but before acknowledgment, RabbitMQ may redeliver; the unique record prevents reapplying local business effects. If the transaction rolls back, the dedup record rolls back with it.

**Do not claim this deduplicates an external shipping-provider call.** A local DB commit cannot atomically include the provider's non-idempotent shipment creation.

## 8. The unavoidable external-shipping ambiguity

Assume the provider has:

- A `create_shipment` API without idempotency support.
- A `lookup_by_merchant_reference` API that is **eventually consistent**.

The consumer requests creation with a stable merchant reference. The provider creates the shipment; then the consumer crashes before saving the provider shipment ID.

After restart, a lookup returns **not found**. This cannot prove creation never occurred: the provider may still be indexing the shipment. Creating again could produce a duplicate shipment.

**Practical policy:**

1. Persist a local shipment operation and unique merchant reference **before** external creation.
2. Record attempts and move operations with uncertain results into `UNKNOWN` / `RECONCILIATION_REQUIRED` state.
3. Reconcile with provider lookups, allowing for documented consistency delays. Avoid assuming an immediate negative response is definitive.
4. If the result remains ambiguous, suspend automatic re-creation and escalate to manual or provider-assisted reconciliation.
5. Only retry creation automatically when evidence is strong enough that a prior shipment did not exist, according to a documented provider contract and business risk policy.

This prioritizes avoiding duplicate shipments over automatic progress during ambiguous failures. That is a business trade-off: potentially delayed fulfillment versus duplicate shipments. If provider capabilities change (e.g., true idempotency keys or enforceable unique merchant references), revisit the decision.

## 9. Event payload and aggregate boundaries

Prefer a stable integration-event schema with `event_id`, event name and version, `order_id`, and only the immutable business facts consumers truly need (for example, customer identifier, book identifier, quantity). **Do not serialize the entire ORM object or domain aggregate.**

Reasons:

- Protects aggregate encapsulation and domain purity.
- Reduces coupling to internal domain refactoring.
- Defines an explicit, versioned consumer contract.
- Avoids synchronous lookup requirements when the consumer needs a small amount of immutable data.

Use separate types for **domain events** (internal facts) and **integration events** (published contracts) if their semantics or lifecycle differ; do not introduce separate types automatically where a direct, well-defined mapping suffices.

## 10. Architectural ownership

| Responsibility | Preferred owner |
|---|---|
| Enforce business invariants; raise domain facts | Domain model |
| Determine transaction boundary and use case | Application service / Unit of Work port |
| Collect events as part of use-case commit | Application orchestration and/or UoW integration (explicitly defined) |
| Map to versioned external event schema | Application boundary mapper or infrastructure adapter, with contract clearly owned |
| Persist outbox in same transaction | Infrastructure / SQLAlchemy implementation of UoW |
| Claim, lease, retry, publish, confirm | Infrastructure worker |
| Implement RabbitMQ transport | Messaging adapter |
| Deduplicate a consumer's DB effects | Consumer application behavior + DB unique constraint |
| Reconcile non-idempotent shipping side effects | Fulfillment application workflow with infrastructure provider adapter |

Do not introduce a framework of generic event buses, dispatchers, registries, and inheritance hierarchies just to publish one event. Start with explicit interfaces for the real boundaries and add abstractions as the use cases justify them.

## 11. Trade-offs and decision record

**Selected:** MySQL outbox + `SKIP LOCKED` short-transaction claiming + expiring lease token + RabbitMQ publisher confirms + at-least-once consumption semantics.

**Why:** Lowest coordination complexity consistent with correct database atomicity, multi-worker scaling, crash recovery, and honest delivery guarantees.

**Accepted limitations:**

- Duplicate messages remain possible.
- An expired lease can allow overlapping publication attempts.
- Publisher confirms cannot be used as globally queryable durable receipts.
- Per-aggregate ordering is not guaranteed by batch `ORDER BY` and must be designed explicitly if required.
- A non-idempotent, eventually consistent external provider leaves an irreducible uncertainty window.
- Retrying only on lease expiry can delay recovery; add targeted retry/backoff controls if operational evidence requires them.

**Not selected:** Redis coordination, database locks held across broker calls, distributed transactions, claimed exactly-once transport guarantees.

**Operational requirements:** Alert on old unpublished events, growing backlog, repeated failure counts, missing publisher confirms, and shipment operations in ambiguous state; measure lease expirations and stale-token completions.

## 12. Validation scenarios for eventual implementation

Before production, test using real MySQL and RabbitMQ where possible:

1. Two publishers claim at the same time and receive nonoverlapping rows.
2. A claim transaction aborts; event remains claimable.
3. A worker crashes before and after publishing.
4. A lost confirm causes a safe retry and consumer deduplication.
5. An expired worker cannot mark a later worker's claim published.
6. An expired worker can still publish, proving duplicates remain possible.
7. Consumer crashes before commit, after commit/before ack, and during redelivery.
8. Shipping API creates successfully but response is lost; lookup is initially negative; reconciliation does not blindly create another shipment.
9. RabbitMQ is unavailable; backlog builds and produces an alert.
10. Multiple events on the same aggregate test whether ordering is actually required.

## 13. Suggested future code layout (not implemented)

These are *proposed paths* for future components, not instructions to add these files now:

```text
src/bookstore_api/
  application/
    ports/
      outbox.py
  infrastructure/
    persistence/
      sqlalchemy_outbox_repository.py
    messaging/
      rabbitmq_publisher.py
      outbox_worker.py
```

When implementation is approved, every added or modified file should be introduced with its exact project-relative path, one component at a time.

## References

- [MySQL 8.4 locking reads and `SKIP LOCKED`](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)
- [RabbitMQ publisher confirms](https://www.rabbitmq.com/docs/confirms)
- [RabbitMQ reliability guidance](https://www.rabbitmq.com/docs/reliability)
- [Transactional Outbox pattern — microservices.io](https://microservices.io/patterns/data/transactional-outbox.html)

---

**Core lesson:** A reliable outbox does not eliminate duplicate delivery. It atomically preserves the obligation to publish; leasing reduces overlapping work; publisher confirms improve certainty; consumers and reconciliation contain the remaining failures. Design for the guarantees the constituent systems actually provide.
