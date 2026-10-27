# API-layer code review findings

Audit of `app/api/v1/*`, `app/services/*`, `app/repositories/*`, `app/models/models.py`,
`app/db/*`. Each finding confirmed against the actual source (file:line). Grouped by
layer, severity-ordered within each group. Nothing in this document has been applied —
it's a record to action later.

## Concurrency / correctness bugs

1. **Idempotent checkout replay doesn't release its lock explicitly**
   `app/services/order_service.py:65-70` — when an idempotency key already has a
   `response_reference`, the function does `return _order_response(db, existing_order)`
   straight out of the `try` block, with no `db.commit()`/`db.rollback()`. The
   `SELECT ... FOR UPDATE` on the `IdempotencyKey` row (line 56) relies on implicit
   session-close rollback instead of an explicit one, unlike every other exit path in
   the same function.
   *Fix:* add `db.rollback()` before the `return` (no writes happened on this path, so
   rollback is correct and releases the lock deterministically).

2. **Cart "add item" quantity cap has a TOCTOU race**
   `app/services/cart_service.py:106-148` (`add_cart_item_service`) reads
   `existing_item.quantity`, computes `new_quantity`, and checks `<= 100` with no row
   lock. Two concurrent "add to cart" calls for the same variant can both read the same
   base quantity and both pass the cap check, exceeding the intended 100-unit limit.
   *Fix:* take a `with_for_update()` lock on the cart item before the read-check-write,
   or do an atomic `UPDATE ... SET quantity = quantity + :n WHERE quantity + :n <= 100
   RETURNING ...` and treat "no row updated" as the cap-exceeded case.

3. **Inventory lock ordering is inconsistent between the two lock sites in checkout**
   `app/services/order_service.py:117-125` sorts `variant_ids` by `str(uuid)` "to
   reduce deadlocks" before calling `lock_inventory`, but the second lock —
   `select(ProductVariant)...with_for_update()` at lines 132-141 — is taken inside
   `for item in cart_items:` in cart-insertion order, not the sorted order. Two
   concurrent checkouts with the same variants in different cart order can still
   deadlock on the `ProductVariant` row locks.
   *Fix:* iterate `cart_items` in the same `variant_ids`-sorted order for the second
   lock loop too.

4. **`category_repository.create_category` has no rollback on failure**
   `app/repositories/category_repository.py:19-31` calls `db.add()` / `db.commit()`
   with no `try/except`, unlike `brand_repository.py` and `product_repository.py`
   (which wrap commit in try/except + rollback). An `IntegrityError` here (e.g. a
   duplicate slug that slipped past the service-layer pre-check) leaves the session in
   a failed-transaction state for the caller.
   *Fix:* wrap in `try/except` with `db.rollback()` on failure, matching the other two
   repositories.

5. **`sort_columns[sort_by]` KeyError risk (currently unreachable, defense-in-depth only)**
   `app/repositories/product_repository.py:109` does `sort_columns[sort_by]` with no
   `.get()`/default. Confirmed `app/api/v1/products.py:31` already constrains
   `sort_by` via `Query(pattern="^(name|created_at|price)$")`, so this can't actually
   be triggered today through the API. Still worth a `.get(sort_by, default_column)`
   so the repository isn't silently relying on the router's validation to avoid a 500.

## Error handling / API consistency

6. **Error→status-code mapping hand-rolled three different, fragile ways**
   - `app/api/v1/orders.py:34-42` — substring match (`"address not found" in
     message.lower()`, etc.).
   - `app/api/v1/brands.py:69-77` — exact message string match
     (`if message == "Brand not found." ...`).
   - `app/api/v1/cart.py:81-86,101-106` — exact message string match
     (`if str(exc) == "Cart item not found."`).
   All three break silently if a service's error message wording changes, and none of
   the three implementations is reused by another router.
   *Fix:* introduce a small typed-exception hierarchy (`NotFoundError`,
   `ConflictError`, `ValidationError`) in a new `app/core/exceptions.py`; have services
   raise the specific type instead of bare `ValueError`; have routers catch by type and
   map to status codes once, consistently.

7. **Router bypasses the service layer, talks to the repository directly**
   `app/api/v1/product_variants.py:68-71` and `97-99` import and call
   `app.repositories.product_variant_repository.get_variant_by_id` directly from the
   router (to check `variant.product_id != product_id`), duplicated in two handlers,
   breaking the router→service→repository layering used everywhere else.
   *Fix:* move the ownership check into `product_variant_service`, called once per
   handler.

8. **Inconsistent 404-vs-400 within the same file**
   `app/api/v1/cart.py:30-37` (`get_cart`) maps every `ValueError` to 400, while
   `update_cart_item`/`remove_cart_item` in the same file special-case "not found" to
   404. Resolves naturally once typed exceptions (finding 6) are in place.

9. **Unbounded pagination on some list endpoints**
   `app/api/v1/addresses.py:16-29` and `app/api/v1/orders.py:55-70` return full,
   unbounded result sets — no `skip`/`limit` — while `app/api/v1/products.py:25-26`
   enforces `Query(..., ge=1, le=100)`.
   *Fix:* add the same bounded `skip`/`limit` query params to both.

10. **Mixed raw-int and `status.HTTP_*` status codes**
    `app/api/v1/products.py` and `product_variants.py` use raw integers
    (`status_code=404`, `400`, `409`), while `brands.py`, `categories.py`, `cart.py`,
    `orders.py`, `auth.py` use `status.HTTP_*` constants.
    *Fix:* standardize on `status.HTTP_*` everywhere.

11. **Duplicate imports (likely file-concatenation artifacts)**
    `app/schemas/order.py:1-7,39-42` imports `datetime`/`UUID`/`BaseModel`/
    `ConfigDict` twice; `app/schemas/category.py:4,6` imports `BaseModel, ConfigDict`
    twice. Harmless but worth a one-line cleanup each.

12. **Same logical field typed two different ways**
    `app/schemas/order.py:28` `CheckoutResponse.status: str` vs `:61`
    `OrderHistoryResponse.status: OrderStatus` — same underlying `Order.status` field.
    *Fix:* make `CheckoutResponse.status` an `OrderStatus` too.

## Data layer / models

13. **Missing index on the `deleted_at` column every repository actually filters on**
    `app/models/models.py:18` — `AuditMixin.deleted_at` (the mixin every model
    inherits) has no `index=True`. The *unused* `SoftDeleteMixin` in
    `app/db/base.py:40-44` does set `index=True`, but no model inherits it — dead code
    masking the real gap. Nearly every repository query filters
    `X.deleted_at.is_(None)`, so most tables are doing full scans for that predicate.
    *Fix:* add `index=True` to `AuditMixin.deleted_at`; remove the unused
    `SoftDeleteMixin`/`TimestampMixin` from `db/base.py`; ship an additive Alembic
    migration for the new index(es).

14. **Missing FK indexes on columns actually queried by**
    `UserAddress.user_id` (`models.py:85`, queried in `order_repository.py:22-27`),
    `DogProfile.user_id` (`models.py:434`), `Review.user_id` (`models.py:503` — only a
    `product_id`+`moderation_status`+`created_at` composite index exists, not usable
    for a user_id lookup). Postgres never auto-indexes FK columns.
    *Fix:* add indexes in the same migration as finding 13.

15. **`get_product_by_slug` skips the eager-load `get_product_by_id` applies**
    `app/repositories/product_repository.py:28-33` doesn't call `_with_active_variants`
    the way `get_product_by_id` (lines 19-25) does — same entity, inconsistent
    behavior; a slug-based lookup that later touches `.variants` triggers an extra
    lazy-load query.
    *Fix:* apply the same eager-load helper in `get_product_by_slug`.

16. **Inconsistent commit ownership between repositories and services**
    `product_repository.py`, `product_variant_repository.py`, `brand_repository.py`,
    `user_repository.py` all call `db.commit()`/`db.rollback()` directly inside the
    repository layer, while `cart_repository.py` and `order_repository.py` use
    `db.flush()` and defer committing to the service/caller. Two incompatible
    transaction-ownership models coexist, which makes it impossible for a service to
    compose multiple repo calls into one atomic transaction when the repo commits
    internally.
    *Fix:* this is a larger refactor (touches every repository file) — worth doing
    deliberately as "repositories never commit, only `flush`; services own
    commit/rollback" rather than bundling it into a quick cleanup pass.

17. **`auth_service.login_user` commits directly, bypassing the repository**
    `app/services/auth_service.py:52-53` — `user.last_login_at = ...; db.commit()`
    skips the repository entirely, unlike every other write in the codebase. If
    `login_user` is ever called from inside a larger transaction, this commit would
    prematurely flush unrelated pending work.
    *Fix:* move the update through a repository function, or at minimum `flush()`
    instead of `commit()` here and let the caller decide.

## Other improvements worth flagging (beyond the original audit)

18. **Asymmetric CRUD coverage across structurally similar resources**
    `app/api/v1/categories.py` only has `GET /` and `POST /` — no `GET /{id}`,
    `PATCH`, or `DELETE` — while `brands.py` and `products.py` have full CRUD.
    `app/api/v1/addresses.py` only has `GET /`, `POST /`, `GET /{id}` — no
    update/delete, even though checkout references `shipping_address_id`, so a wrong
    address can never be corrected or removed by the user. This is new functionality,
    not pure cleanup — worth prioritizing separately since it's a real UX gap (users
    can't edit/delete a saved address at all today).

19. **Business logic in the `addresses` router instead of a service**
    `app/api/v1/addresses.py:56-67` — `create_address` directly queries existing
    default addresses and mutates `item.is_default = False` in a loop inside the
    router. Every other resource (brands/products/categories) routes mutation logic
    through a `*_service` module; addresses has no `address_service.py` at all.
    *Fix:* worth creating one when addresses CRUD is filled out (finding 18) rather
    than patching the router in place twice.

20. **No FK `ondelete` behavior anywhere in `models.py`**
    e.g. `Product.category_id`, `ProductVariant.product_id`, `CartItem.variant_id`,
    `OrderItem.variant_id` all default to `NO ACTION`. Combined with soft-delete-only
    application logic, a hard delete of a parent would raise FK violations rather than
    cascading/nulling predictably. This is a schema-design decision (what *should*
    happen on hard-delete per entity) that deserves its own review, not a blanket
    migration.

21. **Possible N+1 on product list endpoint beyond variants**
    `app/repositories/product_repository.py` (`list_products`) eager-loads `variants`
    only, not `brand`/`category`/`images`. Only worth fixing if the product list
    response schema actually serializes those relationships per item — needs a quick
    check against `app/schemas/product.py` / the router's response model before
    deciding whether this is a real N+1 or a non-issue.

22. **Duplicate-slug check-then-insert is TOCTOU-repeated across three services**
    Near-identical `select(...).where(slug==..., deleted_at.is_(None))` +
    `raise ValueError("already exists")` pattern copy-pasted in `product_service.py`,
    `brand_service.py`, and `category_service.py`. Worth a shared helper once the
    typed-exception work (finding 6) is done — and worth confirming each of those
    tables actually has a DB-level unique constraint on slug, since the check-then-act
    pattern alone isn't race-safe without one.

---

Infrastructure/tooling-level future improvements (testing gaps, CI/CD, frontend
componentization, observability, rate limiting, httpOnly-cookie auth, dependency
tooling, Prettier) are tracked separately in
[`FUTURE_IMPROVEMENTS.md`](./FUTURE_IMPROVEMENTS.md) — this document is scoped to the
application code (API/service/repository/model layers) only.
