import { Fragment, useEffect, useMemo, useState } from "react";
import { Boxes, ClipboardList, FolderTree, LogOut, Package, PawPrint, Plus, Search, Store, Tags, Upload, Users, Warehouse } from "lucide-react";
import { API_BASE_URL, getCurrentUser, loginUser, logoutUser, getAdminProducts, getAdminIngredients, createAdminProduct, updateAdminProduct, deleteAdminProduct, getAdminCategories, saveAdminCategory, deleteAdminCategory, getAdminBrands, saveAdminBrand, deleteAdminBrand, getAdminOrders, createAdminVariant, deleteAdminVariant, uploadAdminImage, linkAdminImage, updateAdminImage, deleteAdminImage, addAdminIngredient, addAdminNutrition, deleteAdminIngredient, deleteAdminNutrition, updateAdminVariant, type AdminProduct, type AdminVariant, type AdminCategory, type AdminBrand, type AdminOrder, type AdminIngredient } from "./api";
import { getAdminInventory, getAdminInventoryLocations, createAdminInventoryLocation, adjustAdminInventory, getAdminInventoryMovements, type AdminInventoryItem, type AdminInventoryLocation, type AdminInventoryMovement } from "./api";
import "./admin.css";

type Section = "dashboard" | "products" | "inventory" | "categories" | "brands" | "orders" | "users";
const nav: { id: Section; label: string; icon: typeof Package }[] = [
  { id: "dashboard", label: "Dashboard", icon: Boxes }, { id: "products", label: "Products", icon: Package }, { id: "inventory", label: "Inventory", icon: Warehouse },
  { id: "categories", label: "Categories", icon: FolderTree }, { id: "brands", label: "Brands", icon: Tags },
  { id: "orders", label: "Orders", icon: ClipboardList }, { id: "users", label: "Users", icon: Users },
];

export default function AdminApp() {
  const pathSection = window.location.pathname.split("/")[2] as Section | undefined;
  const [section, setSection] = useState<Section>(nav.some((item) => item.id === pathSection) ? pathSection! : "dashboard");
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);
  const [loginEmail, setLoginEmail] = useState(""); const [loginPassword, setLoginPassword] = useState("");
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [products, setProducts] = useState<AdminProduct[]>([]); const [ingredients, setIngredients] = useState<AdminIngredient[]>([]); const [categories, setCategories] = useState<AdminCategory[]>([]); const [brands, setBrands] = useState<AdminBrand[]>([]); const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [inventory, setInventory] = useState<AdminInventoryItem[]>([]);
  const [locations, setLocations] = useState<AdminInventoryLocation[]>([]);
  const [movements, setMovements] = useState<AdminInventoryMovement[]>([]);
  const [locationCode, setLocationCode] = useState("");
  const [locationName, setLocationName] = useState("");
  const [selectedVariantId, setSelectedVariantId] = useState("");
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [quantityDelta, setQuantityDelta] = useState("");
  const [adjustmentReason, setAdjustmentReason] = useState("opening_stock");
  const [search, setSearch] = useState(""); const [categoryFilter, setCategoryFilter] = useState("all"); const [sortBy, setSortBy] = useState("created_at"); const [expandedOrderId, setExpandedOrderId] = useState<string | null>(null); const [editingProduct, setEditingProduct] = useState<AdminProduct | null>(null); const [productOpen, setProductOpen] = useState(false);
  const [name, setName] = useState(""); const [slug, setSlug] = useState(""); const [categoryId, setCategoryId] = useState(""); const [brandId, setBrandId] = useState(""); const [description, setDescription] = useState(""); const [shortDescription, setShortDescription] = useState(""); const [status, setStatus] = useState("draft");
  const [fulfillment, setFulfillment] = useState<"internal" | "external_link">("internal"); const [marketplace, setMarketplace] = useState("amazon"); const [externalUrl, setExternalUrl] = useState("");
  const [variantDrafts, setVariantDrafts] = useState([{ sku: "", variant_name: "1 kg", weight_grams: "1000", price: "", currency: "INR", is_active: true }]);
  const [draggedImageId, setDraggedImageId] = useState<string | null>(null);
  const [ingredientName, setIngredientName] = useState(""); const [ingredientPercentage, setIngredientPercentage] = useState(""); const [nutrientCode, setNutrientCode] = useState(""); const [nutrientValue, setNutrientValue] = useState(""); const [nutrientUnit, setNutrientUnit] = useState("g"); const [nutrientBasis, setNutrientBasis] = useState("as_fed");
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [entityName, setEntityName] = useState(""); const [entitySlug, setEntitySlug] = useState(""); const [entityDescription, setEntityDescription] = useState(""); const [entityEditId, setEntityEditId] = useState<number | undefined>();

  useEffect(() => { let active = true; (async () => { try { const user = await getCurrentUser(); if (active && user.roles?.some((role) => role.toLowerCase() === "admin")) setAuthenticated(true); else if (active) { logoutUser(); setError("Administrator access is required."); } } catch { if (active) setAuthenticated(false); } finally { if (active) setChecking(false); } })(); return () => { active = false; }; }, []);
  async function loadAll() { setBusy(true); setError(""); try { const [p, c, b, o, i, inv, loc, mov] = await Promise.all([getAdminProducts(), getAdminCategories(), getAdminBrands(), getAdminOrders(), getAdminIngredients(), getAdminInventory(), getAdminInventoryLocations(), getAdminInventoryMovements()]); setProducts(p); setCategories(c); setBrands(b); setOrders(o); setIngredients(i); setInventory(inv); setLocations(loc); setMovements(mov); if (editingProduct) setEditingProduct(p.find((item) => item.id === editingProduct.id) ?? null); } catch (e) { setError(e instanceof Error ? e.message : "Unable to load admin data."); } finally { setBusy(false); } }
  useEffect(() => { if (authenticated) void loadAll(); }, [authenticated]);
  useEffect(() => { const handlePopState = () => { const path = window.location.pathname.split("/")[2] as Section | undefined; setSection(nav.some((item) => item.id === path) ? path! : "dashboard"); }; window.addEventListener("popstate", handlePopState); return () => window.removeEventListener("popstate", handlePopState); }, []);
  function navigate(next: Section) { setSection(next); window.history.pushState({}, "", next === "dashboard" ? "/admin" : `/admin/${next}`); }
  async function submitLogin(event: React.FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { await loginUser(loginEmail, loginPassword); const user = await getCurrentUser(); if (!user.roles?.some((role) => role.toLowerCase() === "admin")) { logoutUser(); throw new Error("This account does not have administrator access."); } setAuthenticated(true); window.history.replaceState({}, "", "/admin"); setSection("dashboard"); } catch (e) { setError(e instanceof Error ? e.message : "Login failed."); } finally { setBusy(false); } }
  function resetProductForm(product?: AdminProduct) { setEditingProduct(product ?? null); setName(product?.name ?? ""); setSlug(product?.slug ?? ""); setCategoryId(String(product?.category_id ?? categories[0]?.id ?? "")); setBrandId(product?.brand_id ? String(product.brand_id) : ""); setDescription(product?.description ?? ""); setShortDescription(product?.short_description ?? ""); setStatus(product?.status ?? "draft"); setFulfillment(product?.fulfillment_type ?? "internal"); setMarketplace(product?.external_marketplace ?? "amazon"); setExternalUrl(product?.external_url ?? ""); setVariantDrafts([{ sku: "", variant_name: "1 kg", weight_grams: "1000", price: "", currency: "INR", is_active: true }]); setIngredientName(""); setIngredientPercentage(""); setNutrientCode(""); setNutrientValue(""); setNutrientUnit("g"); setNutrientBasis("as_fed"); setProductOpen(true); }
  async function saveProduct(event: React.FormEvent) { event.preventDefault(); setBusy(true); setError(""); try { if (fulfillment === "external_link") { const host = new URL(externalUrl).hostname.toLowerCase(); if (!/^https?:\/\//.test(externalUrl)) throw new Error("External URL must start with https://"); if (marketplace === "amazon" && !(host === "amazon.com" || host.endsWith(".amazon.com") || host === "amazon.in" || host.endsWith(".amazon.in"))) throw new Error("Use a valid Amazon domain."); if (marketplace === "flipkart" && !host.endsWith("flipkart.com")) throw new Error("Use a valid Flipkart domain."); }
    const payload = { name, slug, category_id: Number(categoryId), brand_id: brandId ? Number(brandId) : null, short_description: shortDescription || null, description: description || null, status, fulfillment_type: fulfillment, external_marketplace: fulfillment === "external_link" ? marketplace : null, external_url: fulfillment === "external_link" ? externalUrl : null };
    const product = editingProduct ? await updateAdminProduct(editingProduct.id, payload) : await createAdminProduct(payload);
    if (fulfillment === "internal") { for (const variant of variantDrafts) { if (variant.sku.trim() && variant.price.trim()) await createAdminVariant(product.id, { ...variant, weight_grams: variant.weight_grams ? Number(variant.weight_grams) : null, price: Number(variant.price) }); } }
    await loadAll(); setProductOpen(false);
  } catch (e) { setError(e instanceof Error ? e.message : "Unable to save product."); } finally { setBusy(false); } }
  async function handleImage(product: AdminProduct, file?: File) { if (!file) return; if (!/^image\/(jpeg|png|webp)$/.test(file.type) || !/\.(jpe?g|png|webp)$/i.test(file.name)) { setError("Choose a JPEG, PNG or WebP image."); return; } if (file.size > 10 * 1024 * 1024) { setError("Image must be 10 MB or smaller."); return; } try { setUploadProgress(0); const uploaded = await uploadAdminImage(file, setUploadProgress); const linked = await linkAdminImage(product.id, uploaded.id, file.name, product.images.length === 0); setEditingProduct({ ...product, images: [...product.images, linked] }); await loadAll(); setUploadProgress(null); } catch (e) { setUploadProgress(null); setError(e instanceof Error ? e.message : "Image upload failed."); } }
  async function addIngredient(product: AdminProduct) { if (!ingredientName.trim()) return; try { const existing = ingredients.find((item) => item.name.toLowerCase() === ingredientName.trim().toLowerCase()); await addAdminIngredient(product.id, { ...(existing ? { ingredient_id: existing.id } : { name: ingredientName.trim() }), percentage: ingredientPercentage ? Number(ingredientPercentage) : null, display_order: product.ingredients.length }); setIngredientName(""); setIngredientPercentage(""); await loadAll(); } catch (e) { setError(e instanceof Error ? e.message : "Unable to add ingredient."); } }
  async function addNutrition(product: AdminProduct) { if (!nutrientCode.trim() || !nutrientValue.trim()) return; try { await addAdminNutrition(product.id, { nutrient_code: nutrientCode, value: Number(nutrientValue), unit: nutrientUnit, basis: nutrientBasis }); setNutrientCode(""); setNutrientValue(""); await loadAll(); } catch (e) { setError(e instanceof Error ? e.message : "Unable to add nutrition row."); } }
  function patchVariantDraft(product: AdminProduct, variantId: string, patch: Partial<AdminVariant>) { setEditingProduct((current) => current?.id === product.id ? { ...current, variants: current.variants.map((variant) => variant.id === variantId ? { ...variant, ...patch } : variant) } : current); }
  async function persistVariant(product: AdminProduct, variant: AdminVariant) { try { await updateAdminVariant(product.id, variant.id, { sku: variant.sku, variant_name: variant.variant_name, weight_grams: variant.weight_grams, price: Number(variant.price), currency: variant.currency, is_active: variant.is_active }); await loadAll(); } catch (e) { setError(e instanceof Error ? e.message : "Unable to update variant."); } }
  async function saveEntity(event: React.FormEvent) { event.preventDefault(); try { if (section === "categories") await saveAdminCategory({ name: entityName, slug: entitySlug, description: entityDescription || null }, entityEditId); else await saveAdminBrand({ name: entityName, slug: entitySlug, description: entityDescription || null }, entityEditId); setEntityName(""); setEntitySlug(""); setEntityDescription(""); setEntityEditId(undefined); await loadAll(); } catch (e) { setError(e instanceof Error ? e.message : "Unable to save record."); } }
  async function saveInventoryLocation(event: React.FormEvent) {
    event.preventDefault();
    try {
      await createAdminInventoryLocation({ code: locationCode.trim(), name: locationName.trim() });
      setLocationCode("");
      setLocationName("");
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create warehouse location.");
    }
  }

  async function saveInventoryAdjustment(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedVariantId || !selectedLocationId || !quantityDelta.trim()) {
      setError("Select a product variant and location, then enter a quantity.");
      return;
    }
    const quantity = Number(quantityDelta);
    if (!Number.isInteger(quantity) || quantity === 0) {
      setError("Quantity must be a non-zero whole number.");
      return;
    }
    try {
      await adjustAdminInventory({
        variant_id: selectedVariantId,
        location_id: Number(selectedLocationId),
        quantity_delta: quantity,
        reason: adjustmentReason.trim(),
      });
      setQuantityDelta("");
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to adjust inventory.");
    }
  }

  const visibleProducts = useMemo(() => products
    .filter((p) => `${p.name} ${p.slug}`.toLowerCase().includes(search.toLowerCase()))
    .filter((p) => categoryFilter === "all" || String(p.category_id) === categoryFilter)
    .sort((a, b) => sortBy === "name" ? a.name.localeCompare(b.name) : sortBy === "price" ? Number(a.variants[0]?.price ?? 0) - Number(b.variants[0]?.price ?? 0) : new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
  [products, search, categoryFilter, sortBy]);

  if (checking) return <div className="admin-loading">Checking administrator accessâ€¦</div>;
  if (!authenticated) return <main className="admin-login-page"><form className="admin-login-card" onSubmit={submitLogin}><div className="admin-brand"><PawPrint /> Paw Pantry <span>ADMIN</span></div><h1>Welcome back</h1><p>Sign in with your administrator account.</p>{error && <div className="admin-alert">{error}</div>}<label>Email<input type="email" required value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} /></label><label>Password<input type="password" required value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} /></label><button className="admin-primary" disabled={busy}>{busy ? "Signing inâ€¦" : "Sign in"}</button><a href="/">Back to storefront</a></form></main>;

  return <div className="admin-shell"><aside className="admin-sidebar"><a className="admin-brand" href="/admin"><PawPrint /> Paw Pantry <span>ADMIN</span></a><div className="admin-nav-label">WORKSPACE</div>{nav.map((item) => <button key={item.id} className={section === item.id ? "active" : ""} onClick={() => navigate(item.id)}><item.icon size={17} />{item.label}</button>)}<div className="admin-sidebar-bottom"><a href="/"><Store size={16} /> View storefront</a><button onClick={() => { logoutUser(); setAuthenticated(false); window.location.href = "/admin/login"; }}><LogOut size={16} /> Sign out</button></div></aside>
    <main className="admin-main"><header className="admin-topbar"><div><span className="admin-eyebrow">PAW PANTRY / ADMIN</span><h1>{nav.find((item) => item.id === section)?.label}</h1></div><button className="admin-refresh" onClick={() => void loadAll()}>Refresh data</button></header>
    {error && <div className="admin-alert admin-alert-inline">{error}<button onClick={() => setError("")}>Dismiss</button></div>}
    {section === "dashboard" && <><div className="admin-stats"><div><Package /><span>Products</span><strong>{products.length}</strong></div><div><FolderTree /><span>Categories</span><strong>{categories.length}</strong></div><div><Tags /><span>Brands</span><strong>{brands.length}</strong></div><div><ClipboardList /><span>Orders</span><strong>{orders.length}</strong></div></div><section className="admin-panel"><h2>Recent products</h2><div className="admin-table-wrap"><table><thead><tr><th>Product</th><th>Type</th><th>Status</th></tr></thead><tbody>{products.slice(0, 6).map((p) => <tr key={p.id}><td>{p.name}</td><td>{p.fulfillment_type === "external_link" ? "External link" : "Internal"}</td><td><span className="admin-status">{p.status}</span></td></tr>)}</tbody></table></div></section></>}
    {section === "products" && <section className="admin-panel"><div className="admin-panel-heading"><div><h2>Product catalogue</h2><p>Manage products, variants, images and product information.</p></div><button className="admin-primary" onClick={() => resetProductForm()}><Plus size={16} /> Add product</button></div><div className="admin-toolbar"><div className="admin-search"><Search size={16} /><input placeholder="Search productsâ€¦" value={search} onChange={(e) => setSearch(e.target.value)} /></div><select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}><option value="all">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select><select value={sortBy} onChange={(e) => setSortBy(e.target.value)}><option value="created_at">Newest first</option><option value="name">Name Aâ€“Z</option><option value="price">Price lowâ€“high</option></select></div><div className="admin-table-wrap"><table><thead><tr><th>Product</th><th>Category</th><th>Fulfillment</th><th>Variants</th><th>Status</th><th>Actions</th></tr></thead><tbody>{visibleProducts.map((p) => <tr key={p.id}><td><strong>{p.name}</strong><small>{p.slug}</small></td><td>{categories.find((c) => c.id === p.category_id)?.name ?? "â€”"}</td><td>{p.fulfillment_type === "external_link" ? <span className="admin-pill">External â†—</span> : "Internal"}</td><td>{p.variants.length}</td><td><span className="admin-status">{p.status}</span></td><td className="admin-actions"><button onClick={() => resetProductForm(p)}>Edit</button><button className="danger" onClick={async () => { if (confirm(`Delete ${p.name}?`)) { await deleteAdminProduct(p.id); await loadAll(); } }}>Delete</button></td></tr>)}</tbody></table></div>{visibleProducts.length === 0 && <p className="admin-empty">No products found.</p>}</section>}
    {section === "inventory" && <div className="admin-inventory-page">
      <div className="admin-stats">
        <div><Package /><span>Units on hand</span><strong>{inventory.reduce((sum, item) => sum + item.on_hand, 0)}</strong></div>
        <div><Boxes /><span>Reserved</span><strong>{inventory.reduce((sum, item) => sum + item.reserved, 0)}</strong></div>
        <div><Warehouse /><span>Available</span><strong>{inventory.reduce((sum, item) => sum + item.available, 0)}</strong></div>
      </div>

      <div className="admin-inventory-forms">
        <section className="admin-panel">
          <h2>Adjust stock</h2>
          <p className="admin-helper">Use a positive quantity to add stock or a negative quantity to reduce it.</p>
          <form className="admin-form-grid" onSubmit={saveInventoryAdjustment}>
            <label className="wide">Product variant
              <select required value={selectedVariantId} onChange={(e) => setSelectedVariantId(e.target.value)}>
                <option value="">Select an active internal variant</option>
                {products.filter((product) => product.fulfillment_type === "internal").flatMap((product) =>
                  product.variants.filter((variant) => variant.is_active).map((variant) => (
                    <option key={variant.id} value={variant.id}>{product.name} — {variant.variant_name} ({variant.sku})</option>
                  ))
                )}
              </select>
            </label>
            <label>Warehouse location
              <select required value={selectedLocationId} onChange={(e) => setSelectedLocationId(e.target.value)}>
                <option value="">Select location</option>
                {locations.map((location) => <option key={location.id} value={location.id}>{location.name} ({location.code})</option>)}
              </select>
            </label>
            <label>Quantity change
              <input type="number" step="1" required value={quantityDelta} onChange={(e) => setQuantityDelta(e.target.value)} placeholder="e.g. 25 or -3" />
            </label>
            <label className="wide">Reason
              <input required maxLength={80} value={adjustmentReason} onChange={(e) => setAdjustmentReason(e.target.value)} placeholder="e.g. opening_stock, damaged, restock" />
            </label>
            <div className="wide"><button className="admin-primary" disabled={busy || locations.length === 0}>Save stock adjustment</button></div>
          </form>
          {locations.length === 0 && <p className="admin-helper">Create a warehouse location before adjusting stock.</p>}
        </section>

        <section className="admin-panel">
          <h2>Add warehouse location</h2>
          <p className="admin-helper">Create a location where inventory is physically stored.</p>
          <form className="admin-form-grid" onSubmit={saveInventoryLocation}>
            <label>Location code<input required maxLength={60} value={locationCode} onChange={(e) => setLocationCode(e.target.value)} placeholder="e.g. MAIN-WH" /></label>
            <label>Location name<input required maxLength={160} value={locationName} onChange={(e) => setLocationName(e.target.value)} placeholder="e.g. Main warehouse" /></label>
            <div className="wide"><button className="admin-primary" disabled={busy}>Create location</button></div>
          </form>
        </section>
      </div>

      <section className="admin-panel">
        <div className="admin-panel-heading"><div><h2>Current inventory</h2><p>Stock quantities by product variant and location.</p></div></div>
        <div className="admin-table-wrap"><table>
          <thead><tr><th>Product</th><th>Variant</th><th>SKU</th><th>Location</th><th>On hand</th><th>Reserved</th><th>Available</th></tr></thead>
          <tbody>{inventory.map((item) => <tr key={item.id}>
            <td>{item.product_name}</td><td>{item.variant_name}</td><td>{item.sku}</td><td>{item.location_name}</td>
            <td>{item.on_hand}</td><td>{item.reserved}</td><td><strong>{item.available}</strong></td>
          </tr>)}</tbody>
        </table></div>
        {inventory.length === 0 && <p className="admin-empty">No inventory recorded yet. Create a location and enter the verified opening stock.</p>}
      </section>

      <section className="admin-panel">
        <div className="admin-panel-heading"><div><h2>Stock movement history</h2><p>Audit trail of inventory adjustments.</p></div></div>
        <div className="admin-table-wrap"><table>
          <thead><tr><th>Date</th><th>Product</th><th>Variant</th><th>Location</th><th>Change</th><th>Reason</th></tr></thead>
          <tbody>{movements.map((movement) => <tr key={movement.id}>
            <td>{new Date(movement.created_at).toLocaleString()}</td><td>{movement.product_name}</td><td>{movement.variant_name}</td>
            <td>{movement.location_name}</td><td><strong>{movement.quantity_delta > 0 ? "+" : ""}{movement.quantity_delta}</strong></td><td>{movement.reason}</td>
          </tr>)}</tbody>
        </table></div>
        {movements.length === 0 && <p className="admin-empty">No stock movements recorded yet.</p>}
      </section>
    </div>}
    {(section === "categories" || section === "brands") && <section className="admin-panel"><div className="admin-panel-heading"><div><h2>{section === "categories" ? "Categories" : "Brands"}</h2><p>Manage catalogue organization.</p></div></div><form className="admin-inline-form" onSubmit={saveEntity}><input required placeholder="Name" value={entityName} onChange={(e) => { setEntityName(e.target.value); if (!entityEditId) setEntitySlug(e.target.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")); }} /><input required placeholder="Slug" value={entitySlug} onChange={(e) => setEntitySlug(e.target.value)} /><input placeholder="Description" value={entityDescription} onChange={(e) => setEntityDescription(e.target.value)} /><button className="admin-primary">{entityEditId ? "Update" : "Create"}</button></form><div className="admin-table-wrap"><table><thead><tr><th>Name</th><th>Slug</th><th>Description</th><th>Actions</th></tr></thead><tbody>{(section === "categories" ? categories : brands).map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.slug}</td><td>{item.description ?? "â€”"}</td><td className="admin-actions"><button onClick={() => { setEntityName(item.name); setEntitySlug(item.slug); setEntityDescription(item.description ?? ""); setEntityEditId(item.id); }}>Edit</button><button className="danger" onClick={async () => { if (confirm(`Delete ${item.name}?`)) { if (section === "categories") await deleteAdminCategory(item.id); else await deleteAdminBrand(item.id); await loadAll(); } }}>Delete</button></td></tr>)}</tbody></table></div></section>}
    {section === "orders" && <section className="admin-panel"><div className="admin-panel-heading"><div><h2>Orders</h2><p>Read-only order visibility. Order actions are intentionally disabled.</p></div></div><div className="admin-table-wrap"><table><thead><tr><th>Order</th><th>Date</th><th>Items</th><th>Total</th><th>Status</th></tr></thead><tbody>{orders.map((o) => <Fragment key={o.id}><tr><td>{o.order_number}</td><td>{new Date(o.created_at).toLocaleDateString()}</td><td>{o.items.length}</td><td>{o.currency} {Number(o.total_amount).toFixed(2)}</td><td><span className="admin-status">{o.status}</span></td><td><button className="admin-actions-button" onClick={() => setExpandedOrderId(expandedOrderId === o.id ? null : o.id)}>{expandedOrderId === o.id ? "Hide" : "Details"}</button></td></tr>{expandedOrderId === o.id && <tr key={`${o.id}-detail`}><td colSpan={6}><strong>Order items</strong><ul>{o.items.map((item) => <li key={item.id}>{item.name_snapshot} Ã— {item.quantity} â€” {o.currency} {Number(item.unit_price).toFixed(2)}</li>)}</ul></td></tr>}</Fragment>)}</tbody></table></div></section>}
    {section === "users" && <section className="admin-panel"><h2>Users</h2><p className="admin-empty">User management is not part of this delivery. Role-protected admin authentication is active.</p></section>}
    </main>
    {productOpen && <div className="admin-modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setProductOpen(false); }}><form className="admin-product-modal" onSubmit={saveProduct}><div className="admin-modal-head"><div><span className="admin-eyebrow">CATALOGUE</span><h2>{editingProduct ? "Edit product" : "Create product"}</h2></div><button type="button" onClick={() => setProductOpen(false)}>âœ•</button></div><div className="admin-form-grid"><label>Product name<input required value={name} onChange={(e) => { setName(e.target.value); if (!editingProduct) setSlug(e.target.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")); }} /></label><label>Slug<input required value={slug} onChange={(e) => setSlug(e.target.value)} /></label><label>Category<select required value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>{categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label><label>Brand<select value={brandId} onChange={(e) => setBrandId(e.target.value)}><option value="">No brand</option>{brands.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label><label>Short description<input value={shortDescription} onChange={(e) => setShortDescription(e.target.value)} /></label><label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option><option value="out_of_stock">Out of stock</option></select></label><label className="wide">Description<textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} /></label></div>
      <section className="admin-form-section"><h3>Fulfillment</h3><div className="admin-choice-row"><label><input type="radio" checked={fulfillment === "internal"} onChange={() => setFulfillment("internal")} /> Sold on our store</label><label><input type="radio" checked={fulfillment === "external_link"} onChange={() => setFulfillment("external_link")} /> External marketplace link</label></div>{fulfillment === "external_link" && <div className="admin-form-grid"><label>Marketplace<select value={marketplace} onChange={(e) => setMarketplace(e.target.value)}><option value="amazon">Amazon</option><option value="flipkart">Flipkart</option><option value="other">Other</option></select></label><label>External URL<input type="url" required placeholder="https://â€¦" value={externalUrl} onChange={(e) => setExternalUrl(e.target.value)} /></label>{externalUrl && <a href={externalUrl} target="_blank" rel="noopener noreferrer">Open marketplace preview â†—</a>}</div>}</section>
      {fulfillment === "internal" && <section className="admin-form-section"><h3>Variants</h3>{editingProduct && <ul className="admin-variant-list">{editingProduct.variants.map((variant) => <li key={variant.id} className="admin-existing-variant"><label>SKU<input value={variant.sku} onChange={(e) => patchVariantDraft(editingProduct, variant.id, { sku: e.target.value })} /></label><label>Name<input value={variant.variant_name} onChange={(e) => patchVariantDraft(editingProduct, variant.id, { variant_name: e.target.value })} /></label><label>Weight (g)<input type="number" min="1" value={variant.weight_grams ?? ""} onChange={(e) => patchVariantDraft(editingProduct, variant.id, { weight_grams: e.target.value ? Number(e.target.value) : null })} /></label><label>Price<input type="number" min="0" step="0.01" value={variant.price} onChange={(e) => patchVariantDraft(editingProduct, variant.id, { price: e.target.value })} /></label><label className="admin-variant-active"><input type="checkbox" checked={variant.is_active} onChange={(e) => patchVariantDraft(editingProduct, variant.id, { is_active: e.target.checked })} /> Active</label><button type="button" className="admin-secondary" onClick={() => void persistVariant(editingProduct, variant)}>Save</button><button type="button" className="danger" onClick={async () => { await deleteAdminVariant(editingProduct.id, variant.id); setEditingProduct({ ...editingProduct, variants: editingProduct.variants.filter((item) => item.id !== variant.id) }); await loadAll(); }}>Remove</button></li>)}</ul>}<p className="admin-helper">Add one or more variants. Each row with a SKU and price will be saved.</p>{variantDrafts.map((variant, index) => <div className="admin-form-grid admin-variant-draft" key={index}><label>SKU<input value={variant.sku} onChange={(e) => setVariantDrafts((rows) => rows.map((row, i) => i === index ? { ...row, sku: e.target.value } : row))} placeholder="SKU-001" /></label><label>Variant name<input value={variant.variant_name} onChange={(e) => setVariantDrafts((rows) => rows.map((row, i) => i === index ? { ...row, variant_name: e.target.value } : row))} /></label><label>Weight (grams)<input type="number" min="1" value={variant.weight_grams} onChange={(e) => setVariantDrafts((rows) => rows.map((row, i) => i === index ? { ...row, weight_grams: e.target.value } : row))} /></label><label>Price (INR)<input type="number" min="0" step="0.01" value={variant.price} onChange={(e) => setVariantDrafts((rows) => rows.map((row, i) => i === index ? { ...row, price: e.target.value } : row))} /></label><button type="button" className="admin-secondary" onClick={() => setVariantDrafts((rows) => rows.length === 1 ? [{ sku: "", variant_name: "1 kg", weight_grams: "1000", price: "", currency: "INR", is_active: true }] : rows.filter((_, i) => i !== index))}>Remove row</button></div>)}<button type="button" className="admin-secondary" onClick={() => setVariantDrafts((rows) => [...rows, { sku: "", variant_name: "", weight_grams: "", price: "", currency: "INR", is_active: true }])}>+ Add variant</button></section>}
      <div className="admin-modal-actions"><button type="button" className="admin-secondary" onClick={() => setProductOpen(false)}>Cancel</button><button className="admin-primary" disabled={busy}>{busy ? "Savingâ€¦" : "Save product"}</button></div>
      {editingProduct && <div className="admin-extra-sections"><section className="admin-form-section"><h3>Images</h3><label className="admin-upload"><Upload size={17} /> Upload image<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => void handleImage(editingProduct, e.target.files?.[0])} /></label>{uploadProgress !== null && <div className="admin-progress"><span style={{ width: `${uploadProgress}%` }} />Uploading imageâ€¦ {uploadProgress}%</div>}<div className="admin-image-list">{editingProduct.images.map((image, index) => <div key={image.id} draggable onDragStart={() => setDraggedImageId(image.id)} onDragOver={(event) => event.preventDefault()} onDrop={async (event) => { event.preventDefault(); if (!draggedImageId || draggedImageId === image.id) return; const from = editingProduct.images.findIndex((item) => item.id === draggedImageId); const to = index; const reordered = [...editingProduct.images]; const [moved] = reordered.splice(from, 1); reordered.splice(to, 0, moved); for (let position = 0; position < reordered.length; position++) await updateAdminImage(editingProduct.id, reordered[position].id, { position }); setDraggedImageId(null); await loadAll(); }}><img src={image.media_asset.url?.startsWith("http") ? image.media_asset.url : `${API_BASE_URL.replace(/\/api\/v1$/, "")}${image.media_asset.url ?? `/media/${image.media_asset.object_key}`}`} alt={image.alt_text ?? "Product"} /><button type="button" onClick={async () => { await updateAdminImage(editingProduct.id, image.id, { is_primary: true }); setEditingProduct({ ...editingProduct, images: editingProduct.images.map((item) => ({ ...item, is_primary: item.id === image.id })) }); await loadAll(); }}>{image.is_primary ? "â˜… Primary" : "â˜† Primary"}</button><button type="button" disabled={index === 0} onClick={async () => { await updateAdminImage(editingProduct.id, image.id, { position: Math.max(0, image.position - 1) }); await loadAll(); }}>â†‘</button><button type="button" disabled={index === editingProduct.images.length - 1} onClick={async () => { await updateAdminImage(editingProduct.id, image.id, { position: image.position + 1 }); await loadAll(); }}>â†“</button><button type="button" onClick={async () => { await deleteAdminImage(editingProduct.id, image.id); setEditingProduct({ ...editingProduct, images: editingProduct.images.filter((item) => item.id !== image.id) }); await loadAll(); }}>Remove</button></div>)}</div></section><section className="admin-form-section"><h3>Ingredients</h3><div className="admin-inline-form"><input list="admin-ingredients" placeholder="Select or create ingredient" value={ingredientName} onChange={(e) => setIngredientName(e.target.value)} /><datalist id="admin-ingredients">{ingredients.map((item) => <option key={item.id} value={item.name} />)}</datalist><input type="number" min="0" max="100" placeholder="%" value={ingredientPercentage} onChange={(e) => setIngredientPercentage(e.target.value)} /><button type="button" className="admin-primary" onClick={() => void addIngredient(editingProduct)}>Add</button></div><ul>{editingProduct.ingredients.map((i) => <li key={i.id}>{i.ingredient_name} {i.percentage == null ? "" : `â€” ${i.percentage}%`} <button type="button" onClick={async () => { await deleteAdminIngredient(editingProduct.id, i.id); setEditingProduct({ ...editingProduct, ingredients: editingProduct.ingredients.filter((item) => item.id !== i.id) }); await loadAll(); }}>Remove</button></li>)}</ul></section><section className="admin-form-section"><h3>Nutrition</h3><div className="admin-inline-form"><input placeholder="Nutrient code" value={nutrientCode} onChange={(e) => setNutrientCode(e.target.value)} /><input type="number" min="0" step="0.00001" placeholder="Value" value={nutrientValue} onChange={(e) => setNutrientValue(e.target.value)} /><input placeholder="Unit" value={nutrientUnit} onChange={(e) => setNutrientUnit(e.target.value)} /><input placeholder="Basis" value={nutrientBasis} onChange={(e) => setNutrientBasis(e.target.value)} /><button type="button" className="admin-primary" onClick={() => void addNutrition(editingProduct)}>Add</button></div><ul>{editingProduct.nutrition.map((n) => <li key={n.id}>{n.nutrient_code}: {n.value} {n.unit} ({n.basis}) <button type="button" onClick={async () => { await deleteAdminNutrition(editingProduct.id, n.id); setEditingProduct({ ...editingProduct, nutrition: editingProduct.nutrition.filter((item) => item.id !== n.id) }); await loadAll(); }}>Remove</button></li>)}</ul></section></div>}
    </form></div>}
  </div>;
}
