# Admin dashboard + backend completion: products, cart/buy, external marketplace links, secure images, S3/local toggle

## Context

Storefront (cart, checkout, auth) already works. There is **no admin UI at all** today — `frontend/src/App.tsx` is a single 1677-line customer-facing page with no router. Backend has partial admin CRUD (`require_admin`-gated) for products, variants, brands, categories, but:

- No way to attach images to a product (upload endpoint exists at `/media/images` but nothing links a `MediaAsset` to a `Product`).
- No ingredients / nutrition admin endpoints, though the tables exist (`ProductIngredient`, `NutritionalAnalysis`).
- No inventory admin endpoints (`Inventory`, `InventoryMovement`, `InventoryLocation` exist but unmanaged).
- No concept of a product that is **sold only via an external marketplace link** (Amazon/Flipkart) vs one sold on our own site. The model/schema has nothing for this.
- Image upload (`app/services/secure_image_upload.py`) is already well hardened (Pillow re-encode to WebP, format allowlist, EXIF stripped, ClamAV scan, opaque filename) — an `.exe` renamed `.jpg` is already rejected because Pillow can't decode it and it gets re-encoded, not stored as-is. This plan keeps that pipeline and only adds a storage-backend switch (local disk now, S3 later) behind a flag, since there's no S3 access yet.
- Category CRUD is missing `update`/`delete` (brand has them, category doesn't) — needed for a real admin screen.

Goal: finish the backend admin surface (full field coverage, image linking, external-link products) and build a real Admin dashboard in the frontend, plus fix the storefront's cart/buy flow to behave correctly for both normal and external-link products.

## 1. Backend model changes (new Alembic migration)

In `app/models/models.py`:

- Add to `Product`:
  - `fulfillment_type: Mapped[ProductFulfillmentType]` enum `INTERNAL` (default) / `EXTERNAL_LINK`.
  - `external_url: Mapped[Optional[str]]` (String 2048).
  - `external_marketplace: Mapped[Optional[ProductMarketplace]]` enum `AMAZON` / `FLIPKART` / `OTHER`, nullable.
  - `CheckConstraint`: when `fulfillment_type = EXTERNAL_LINK`, `external_url` must be set (enforced in service layer with a clear ValueError; DB check constraints can't easily reference enum conditionals portably, so keep that validation in `product_service.py`).
- Add to `MediaAsset`:
  - `storage_backend: Mapped[StorageBackend]` enum `LOCAL` / `S3`, default from settings at write time.
- New migration via `alembic revision --autogenerate -m "add product external link and media storage backend"`, reviewed by hand (enum creation, nullable columns, no data loss).

## 2. Backend config (`app/core/config.py`)

Add:
```python
storage_backend: str = "local"   # "local" | "s3"
s3_bucket: str | None = None
s3_region: str | None = None
s3_access_key_id: str | None = None
s3_secret_access_key: str | None = None
s3_endpoint_url: str | None = None   # optional, for S3-compatible/minio
```
Default stays `local` since there's no S3 access yet; switching to `s3` later is a pure config change once credentials exist.

## 3. Storage abstraction (`app/services/storage.py`, new)

Extract a small interface used by `media.py`:
```python
class StorageBackend(Protocol):
    def save(self, data: bytes, extension: str) -> str: ...  # returns object_key
    def url_for(self, object_key: str) -> str: ...

class LocalStorage:   # wraps existing persist_image() from secure_image_upload.py
class S3Storage:      # boto3 put_object; only imported/instantiated when storage_backend == "s3"

def get_storage() -> StorageBackend:  # picks backend from get_settings().storage_backend
```
- `LocalStorage.save` reuses `persist_image()` unchanged (already safe: opaque key, path-escape guard).
- `S3Storage.save` uploads the already-normalized/scanned bytes (never raw upload bytes) with `ContentType=mime_type`, key `uuid4().hex + extension`; `boto3` added to `requirements.txt`/`pyproject.toml` as an optional dependency, imported lazily inside `S3Storage` so local-only deployments don't need it installed.
- `url_for`: local → `/media/{key}` (existing static mount); s3 → public bucket URL or `s3_endpoint_url` + key (presigned URL left as a documented follow-up, out of scope since no bucket exists yet).
- `media.py` upload handler calls `get_storage()` instead of `persist_image()` directly, and sets `MediaAsset.storage_backend` to whatever backend actually wrote the file.

This satisfies "upload to S3 or local based on flag, default local since no S3 access" without requiring AWS creds to run today.

## 4. Product image linking — new `app/api/v1/product_images.py`

Mirrors `product_variants.py` pattern (`prefix="/products/{product_id}/images"`, `require_admin` on writes):
- `POST /` — body `{media_asset_id, alt_text?, is_primary?}` → creates `ProductImage`, auto-assigns next `position`; if `is_primary=True`, unset previous primary for that product.
- `PATCH /{image_id}` — update `alt_text`, `is_primary`, `position`.
- `DELETE /{image_id}`.
- `GET /` — public, ordered by `position` (already have `Product.images` relationship ordered).
New `app/schemas/product_image.py` (`ProductImageCreate/Update/Response`), `app/services/product_image_service.py`, `app/repositories` not strictly needed — keep logic in service to match existing lighter services (e.g. `brand_service.py`).

Admin image workflow becomes: `POST /media/images` (upload+scan+normalize) → get `media_asset_id` → `POST /products/{id}/images` (link it). This two-step flow also lets the same media asset be reused across products if ever needed.

## 5. Ingredients & nutrition admin endpoints

- `app/schemas/ingredient.py`: `IngredientCreate/Response`, `ProductIngredientCreate/Update/Response` (`ingredient_id or {name, description}` inline-create, `percentage`, `display_order`).
- `app/schemas/nutrition.py`: `NutritionalAnalysisCreate/Update/Response` (`nutrient_code`, `value`, `unit`, `basis`).
- `app/api/v1/ingredients.py`: `GET/POST /ingredients` (admin create, public list for autocomplete).
- Extend `app/api/v1/products.py` (or new `product_ingredients.py` / `product_nutrition.py` following the variants pattern) with nested routes `products/{id}/ingredients`, `products/{id}/nutrition` — admin CRUD, public GET.
- Service functions in `product_service.py` or new small services, same pattern as `product_variant_service.py`.

## 6. Product schema/response — expose everything the admin form needs

`app/schemas/product.py`:
- `ProductCreate`/`ProductUpdate`: add `fulfillment_type`, `external_url`, `external_marketplace`. Validator: if `fulfillment_type == EXTERNAL_LINK`, `external_url` required and must be `http(s)://` (use `pydantic.AnyHttpUrl` or a regex check) and host should be one of amazon/flipkart domains when marketplace is AMAZON/FLIPKART (soft validation — warn, don't block OTHER).
- `ProductResponse`: add `fulfillment_type`, `external_url`, `external_marketplace`, `images: list[ProductImageResponse]`, `ingredients: list[ProductIngredientResponse]`, `nutrition: list[NutritionalAnalysisResponse]` so one admin "get product" call hydrates the whole edit form, and the storefront gets everything needed to render.

`product_service.py`: validation for the external-link invariant lives here (raise `ValueError` → existing `products.py` handlers already map `ValueError` → 400).

## 7. Category CRUD completion

Add `update_category_service`/`delete_category_service` in `category_service.py` (same shape as `brand_service.py`'s), `CategoryUpdate` schema, `PATCH`/`DELETE /categories/{id}` in `categories.py` — needed so the admin Categories screen isn't read-only-create-only.

## 8. Cart / Buy Now — backend

Cart/checkout already works (`cart.py`, `orders.py`). Backend needs one guard: `cart_service.add_item` (or wherever `CartItem` is created) must reject adding a variant whose `Product.fulfillment_type == EXTERNAL_LINK` with a clear 400 ("This product is only available via the external listing"), since such products have no real checkout flow. Check `app/services/cart_service.py` for the add-item function and add this check next to existing validation (inventory/active checks).

## 9. Frontend: routing + admin shell

- Add `react-router-dom` to `frontend/package.json`.
- Split `App.tsx`: extract the current storefront JSX into `src/pages/Storefront.tsx` (or keep as `StorefrontApp`), add `src/pages/admin/` tree, wire up in `App.tsx`:
  - `/` ... existing storefront routes (kept as-is, just moved behind the router).
  - `/admin/login` — reuse existing login API (`loginUser` in `api.ts`), after login verify `/auth/me` roles includes `admin` (extend `UserResponse` type to include `roles: string[]` — backend `auth.py` `/auth/me` likely needs to include roles too; check and extend if missing).
  - `/admin` — `AdminLayout` (sidebar: Dashboard, Products, Categories, Brands, Orders, Users) + `<Outlet/>`, guarded by an `AdminGuard` component that redirects to `/admin/login` if not authenticated or not admin.
- New admin-only CSS file `src/admin.css` reusing the existing design tokens (`--green`, `--green-deep`, `--cream`, `--orange`, `--sage`, `--muted`, `--line`) for visual consistency with the storefront, but laid out as a proper dashboard (fixed sidebar, content area, data tables, modals/drawers for forms) — not a copy of storefront page chrome.

## 10. Frontend: admin API client

Extend `src/api.ts` (or new `src/adminApi.ts`) with typed functions for every new/existing admin endpoint: products (create/update/delete/list with filters), product images (upload via `/media/images` then link via `/products/{id}/images`), variants, ingredients, nutrition, categories (incl. update/delete), brands (already has update/delete pattern to copy), orders (admin list — check `orders.py` for an admin list endpoint; add one if missing, e.g. `GET /orders` admin-only paginated list, since currently it looks checkout/user-scoped only).

## 11. Frontend: Admin Products screen (the core deliverable)

`src/pages/admin/ProductsList.tsx`: table with search/filter/sort (reuse `GET /products` params already supported), status badges, fulfillment-type badge (Internal / External ↗).

`src/pages/admin/ProductForm.tsx` (create + edit), sectioned form covering **every field**:
- Basics: name, slug (auto-generate from name, editable), brand (select), category (select), short description, description, status.
- **Fulfillment**: radio/toggle "Sold on our store" vs "External marketplace link". When external: marketplace select (Amazon/Flipkart/Other) + URL input with client-side `https://` + domain-pattern validation and a live preview link ("Open ↗").
- Variants: repeatable rows (sku, name, weight, price, currency, active) with add/remove, calling variant endpoints.
- Images: drag-and-drop/file-picker uploader →
  1. Client-side pre-check: reject by extension/MIME before upload (`accept="image/jpeg,image/png,image/webp"` on the input **and** a JS check of `file.type`/magic-byte sniff is NOT solely trusted — server already re-validates via Pillow+ClamAV, this is just fast UX feedback) — show inline error for `.exe`/wrong type/too large without a round trip.
  2. Upload to `/media/images`, show progress, then auto-link via `/products/{id}/images`, with drag-to-reorder (`PATCH` position) and a "set primary" star.
- Ingredients: add-existing-or-create-new combobox + percentage + ordering.
- Nutrition: repeatable rows (nutrient code, value, unit, basis).
- Inventory (optional stretch, flag clearly as follow-up if time-boxed): per-variant stock by location.

`src/pages/admin/Categories.tsx`, `src/pages/admin/Brands.tsx`: simple CRUD tables + modal forms (brands pattern already fully supported by backend; categories needs step 7 first).

`src/pages/admin/Orders.tsx`: read-only order list/detail (status, items, totals) — admin visibility only, no destructive actions in this pass.

## 12. Storefront: fix Add to Cart / Buy Now for both product kinds

In the storefront product card/detail component inside `App.tsx` (or wherever `addCartItem` is currently called):
- If `product.fulfillment_type === "external_link"`: **always** hide "Add to Cart"/"Buy Now" and show only a single external link button — regardless of marketplace (Amazon, Flipkart, or Other/any other retailer). Label reflects the marketplace: "Buy on Amazon ↗" / "Buy on Flipkart ↗" / "View on seller's site ↗" for `OTHER`. Rendered as a plain `<a href={product.external_url} target="_blank" rel="noopener noreferrer">` — no cart call at all, no exceptions. This matches the backend guard in step 8 as defense-in-depth, not the primary control.
- If internal: keep/add two actions — "Add to Cart" (existing `addCartItem` flow) and a new **"Buy Now"** button that calls `addCartItem` then immediately navigates to checkout (reuses existing checkout screen/flow in `App.tsx`, just a one-click shortcut instead of a separate backend endpoint — no new backend route needed since checkout already takes a cart state).

## Verification

- Backend: `alembic upgrade head` applies cleanly; `pytest` (existing `tests/`) still green; manually hit new endpoints via FastAPI `/docs` — create an external-link product (expect 400 without `external_url`), link an uploaded image, add ingredients/nutrition, confirm `GET /products/{id}` returns the full hydrated object.
- Try uploading a `.exe` renamed to `.jpg` through `/media/images` — confirm still rejected (Pillow decode failure) — no behavior change there, just regression-check after refactor into `storage.py`.
- Set `STORAGE_BACKEND=local` (default) — confirm uploads still land in `UPLOAD_DIR` and are servable at `/media/{key}`.
- Frontend: `npm run dev`, log in as a seeded admin user, walk through: create product → toggle external-link mode and verify form switches correctly → create internal product → upload an image (try a bad file first to confirm client-side rejection, then a good one) → add variant/ingredient/nutrition row → verify it shows correctly on the public storefront, including the "Buy on Amazon ↗" button for the external product and Add-to-Cart/Buy-Now for the internal one → complete a real cart→checkout run end to end.
