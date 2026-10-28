
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  Heart,
  Leaf,
  Menu,
  PawPrint,
  Search,
  ShoppingBag,
  ShieldCheck,
  Star,
  Truck,
  X,
} from "lucide-react";
import "./App.css";

import {
  addCartItem,
  getCart,
  loginUser,
  logoutUser,
  updateCartItem,
  removeCartItem,
  getAddresses,
  createAddress,
  checkoutOrder,
  type CartResponse,
  type ShippingAddress,
  type CheckoutResponse,
} from "./api";

type Product = {
  id: string;
  variantId: string;
  name: string;
  category: string;
  size: string;
  price: number;
  currency: string;
  rating: number;
  color: string;
  accent: string;
  tag?: string;
};

type ApiProduct = {
  id: string;
  name: string;
  category_id: number;
  short_description: string | null;
  variants: {
    id: string;
    variant_name: string;
    price: string | number;
    currency: string;
    is_active: boolean;
  }[];
};

const categoryNames: Record<number, string> = {
  1: "Dry Food",
  2: "Wet Food",
  3: "Treats",
  4: "Supplements",
};

const productStyles: Record<string, { color: string; accent: string; rating: number; tag?: string }> = {
  "chicken-brown-rice": { color: "#e5a36c", accent: "#bd5730", rating: 4.9, tag: "Best Seller" },
  "salmon-sweet-potato": { color: "#4f88bb", accent: "#214f80", rating: 4.8, tag: "Popular" },
  "puppy-growth-formula": { color: "#e8ae44", accent: "#bc7220", rating: 4.9 },
  "chicken-gravy-meal": { color: "#e5a36c", accent: "#bd5730", rating: 4.8 },
  "joint-care-chews": { color: "#6a9c79", accent: "#285c45", rating: 4.7 },
};

function mapApiProduct(apiProduct: ApiProduct): Product | null {
  const variants = apiProduct.variants
    .filter((variant) => variant.is_active)
    .sort((a, b) => Number(a.price) - Number(b.price));
  const variant = variants[0];
  if (!variant) return null;

  const slug = apiProduct.name
    .toLowerCase()
    .replace(/ & /g, "-")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const style = productStyles[slug] ?? { color: "#e2e9d7", accent: "#285c45", rating: 4.8 };

  
return {
  id: apiProduct.id,
  variantId: variant.id,
  name: apiProduct.name,
  category: categoryNames[apiProduct.category_id] ?? "Dog Food",
  size: variant.variant_name,
  price: Number(variant.price),
  currency: variant.currency,
  rating: style.rating,
  color: style.color,
  accent: style.accent,
  tag: style.tag,
};
}


type OrderHistoryItem = {
  id: string;
  variant_id: string | null;
  sku_snapshot: string;
  name_snapshot: string;
  unit_price: string | number;
  quantity: number;
};

type OrderHistory = {
  id: string;
  order_number: string;
  status: string;
  currency: string;
  subtotal_amount: string | number;
  shipping_amount: string | number;
  tax_amount: string | number;
  discount_amount: string | number;
  total_amount: string | number;
  shipping_address_snapshot: Record<string, unknown>;
  created_at: string;
  items: OrderHistoryItem[];
};

type OrderShipment = {
  id: string;
  carrier: string | null;
  tracking_number: string | null;
  status: string;
  shipped_at: string | null;
  delivered_at: string | null;
  created_at: string;
};

type OrderStatusEvent = {
  id: string;
  old_status: string | null;
  new_status: string;
  reason: string | null;
  created_at: string;
};

type OrderDetail = OrderHistory & {
  billing_address_snapshot: Record<string, unknown> | null;
  shipments: OrderShipment[];
  status_history: OrderStatusEvent[];
};

const checkoutInputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid #d8dfd1",
  borderRadius: 10,
  padding: "11px 12px",
  background: "white",
  font: "inherit",
};

const categories = [
  { name: "Dry Food", icon: "🥣", color: "#f3dfc6" },
  { name: "Wet Food", icon: "🥩", color: "#f4dfce" },
  { name: "Treats", icon: "🦴", color: "#f3e4d0" },
  { name: "Supplements", icon: "🌿", color: "#e2e9d7" },
  { name: "Accessories", icon: "🎾", color: "#f6e5d1" },
];

function ProductPack({ product }: { product: Product }) {
  return (
    <div
      className="product-pack"
      style={
        {
          "--pack-color": product.color,
          "--pack-accent": product.accent,
        } as React.CSSProperties
      }
      aria-label={`${product.name} product packaging`}
    >
      <div className="pack-seal" />
      <div className="pack-brand">
        <PawPrint size={13} />
        <span>paw pantry</span>
      </div>
      <div className="pack-name">{product.name}</div>
      <div className="pack-dog">🐕</div>
      <div className="pack-food">✦ ✦ ✦</div>
      <div className="pack-weight">{product.size}</div>
    </div>
  );
}

function App() {
  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(true);
  const [productsError, setProductsError] = useState("");
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [cartLoading, setCartLoading] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(
  Boolean(localStorage.getItem("paw_pantry_access_token")),
  );
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [wishlist, setWishlist] = useState<string[]>([]);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [ordersOpen, setOrdersOpen] = useState(false);
  const [orders, setOrders] = useState<OrderHistory[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null);
  const [orderDetailLoading, setOrderDetailLoading] = useState(false);
  const [orderDetailError, setOrderDetailError] = useState("");
  const [addresses, setAddresses] = useState<ShippingAddress[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const [addressFormOpen, setAddressFormOpen] = useState(false);
  const [addressSaving, setAddressSaving] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [checkoutError, setCheckoutError] = useState("");
  const [completedOrder, setCompletedOrder] = useState<CheckoutResponse | null>(null);
  const [addressForm, setAddressForm] = useState({
    recipient_name: "",
    phone: "",
    line1: "",
    line2: "",
    city: "",
    state_region: "",
    postal_code: "",
    country_code: "IN",
    is_default: false,
  });

  useEffect(() => {
    const controller = new AbortController();

    async function loadProducts() {
      try {
        setProductsLoading(true);
        setProductsError("");
        const response = await fetch("http://127.0.0.1:8000/api/v1/products/", {
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Products API returned ${response.status}`);
        }
        const data: ApiProduct[] = await response.json();
        setProducts(
          data
            .map(mapApiProduct)
            .filter((product): product is Product => product !== null),
        );
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        setProductsError(
          error instanceof Error ? error.message : "Unable to load products.",
        );
      } finally {
        if (!controller.signal.aborted) setProductsLoading(false);
      }
    }

    void loadProducts();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!isLoggedIn) {
      setCart(null);
      return;
    }

    void refreshCart();
  }, [isLoggedIn]);

  const filteredProducts = useMemo(() => {
    const term = search.trim().toLowerCase();

    return products.filter((product) => {
      const matchesSearch =
        !term ||
        product.name.toLowerCase().includes(term) ||
        product.category.toLowerCase().includes(term);

      const matchesCategory =
        activeCategory === "All" || product.category === activeCategory;

      return matchesSearch && matchesCategory;
    });
  }, [products, search, activeCategory]);

  
  async function addToCart(product: Product) {
  if (!isLoggedIn) {
    setCartOpen(false);
    setLoginOpen(true);
    setNotice("Please log in before adding items to your cart.");
    return;
  }

  try {
    setCartLoading(true);

    const updatedCart = await addCartItem(product.variantId, 1);
    setCart(updatedCart);
    setNotice(`${product.name} added to your cart.`);
  } catch (error) {
    setNotice(
      error instanceof Error ? error.message : "Unable to add item to cart.",
    );
  } finally {
    setCartLoading(false);
  }
  }

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setCartLoading(true);
      await loginUser(loginEmail, loginPassword);
      setIsLoggedIn(true);
      const currentCart = await getCart();
      setCart(currentCart);
      setLoginPassword("");
      setLoginOpen(false);
      setNotice("Logged in successfully.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Login failed.");
    } finally {
      setCartLoading(false);
    }
  }

  function handleLogout() {
    logoutUser();
    setIsLoggedIn(false);
    setCart(null);
    setCartOpen(false);
    setLoginOpen(false);
    setNotice("You have been logged out.");
  }

  async function refreshCart() {
    try {
      setCartLoading(true);
      const currentCart = await getCart();
      setCart(currentCart);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load your cart.";
      const normalizedMessage = message.toLowerCase();
      if (
        message.includes("401") ||
        normalizedMessage.includes("token") ||
        normalizedMessage.includes("not authenticated") ||
        normalizedMessage.includes("unauthorized")
      ) {
        logoutUser();
        setIsLoggedIn(false);
        setCart(null);
        setNotice("Your session has expired. Please log in again.");
      } else {
        setNotice(message);
      }
    } finally {
      setCartLoading(false);
    }
  }

  async function changeCartQuantity(itemId: string, quantity: number) {
    try {
      setCartLoading(true);
      const updatedCart = await updateCartItem(itemId, quantity);
      setCart(updatedCart);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to update quantity.");
    } finally {
      setCartLoading(false);
    }
  }

  async function deleteCartItem(itemId: string) {
    try {
      setCartLoading(true);
      const updatedCart = await removeCartItem(itemId);
      setCart(updatedCart);
      setNotice("Item removed from your cart.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to remove item.");
    } finally {
      setCartLoading(false);
    }
  }

  async function openCheckout() {
    if (!isLoggedIn) {
      setCartOpen(false);
      setLoginOpen(true);
      setNotice("Please log in before checking out.");
      return;
    }
    if (!cart || cart.items.length === 0) {
      setNotice("Your cart is empty.");
      return;
    }
    setCheckoutOpen(true);
    setCartOpen(false);
    setCheckoutError("");
    setCompletedOrder(null);
    try {
      setCheckoutLoading(true);
      const savedAddresses = await getAddresses();
      setAddresses(savedAddresses);
      const defaultAddress = savedAddresses.find((address) => address.is_default) ?? savedAddresses[0];
      setSelectedAddressId(defaultAddress?.id ?? "");
      setAddressFormOpen(savedAddresses.length === 0);
    } catch (error) {
      setCheckoutError(error instanceof Error ? error.message : "Unable to load saved addresses.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  async function saveAddress(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAddressSaving(true);
    setCheckoutError("");
    try {
      const saved = await createAddress({
        ...addressForm,
        phone: addressForm.phone.trim() || null,
        line2: addressForm.line2.trim() || null,
      });
      const updated = addressForm.is_default
        ? [saved, ...addresses.filter((address) => address.id !== saved.id).map((address) => ({ ...address, is_default: false }))]
        : [...addresses, saved];
      setAddresses(updated);
      setSelectedAddressId(saved.id);
      setAddressFormOpen(false);
      setAddressForm({
        recipient_name: "",
        phone: "",
        line1: "",
        line2: "",
        city: "",
        state_region: "",
        postal_code: "",
        country_code: "IN",
        is_default: false,
      });
      setNotice("Shipping address saved.");
    } catch (error) {
      setCheckoutError(error instanceof Error ? error.message : "Unable to save the address.");
    } finally {
      setAddressSaving(false);
    }
  }

  async function placeOrder() {
    if (!selectedAddressId) {
      setCheckoutError("Please select or add a shipping address.");
      return;
    }
    setCheckoutLoading(true);
    setCheckoutError("");
    try {
      const order = await checkoutOrder({
        shipping_address_id: selectedAddressId,
        idempotency_key: crypto.randomUUID(),
      });
      setCompletedOrder(order);
      await refreshCart();
      setNotice("Your order has been placed successfully.");
    } catch (error) {
      setCheckoutError(error instanceof Error ? error.message : "Unable to place your order.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  async function openMyOrders() {
    if (!isLoggedIn) {
      setLoginOpen(true);
      setNotice("Please log in to view your orders.");
      return;
    }

    setOrdersOpen(true);
    setOrderDetail(null);
    setOrderDetailError("");
    setOrdersLoading(true);
    setOrdersError("");
    try {
      const token = localStorage.getItem("paw_pantry_access_token");
      const response = await fetch("http://127.0.0.1:8000/api/v1/orders/", {
        headers: {
          Accept: "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Unable to load orders (${response.status}).`);
      }
      const data: OrderHistory[] = await response.json();
      setOrders(data);
    } catch (error) {
      setOrdersError(error instanceof Error ? error.message : "Unable to load your orders.");
    } finally {
      setOrdersLoading(false);
    }
  }

  async function loadOrderDetail(orderId: string) {
    setOrderDetailLoading(true);
    setOrderDetailError("");
    setOrderDetail(null);
    try {
      const token = localStorage.getItem("paw_pantry_access_token");
      const response = await fetch(`http://127.0.0.1:8000/api/v1/orders/${orderId}`, {
        headers: {
          Accept: "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Unable to load order details (${response.status}).`);
      }
      setOrderDetail(await response.json() as OrderDetail);
    } catch (error) {
      setOrderDetailError(error instanceof Error ? error.message : "Unable to load order details.");
    } finally {
      setOrderDetailLoading(false);
    }
  }

  function formatOrderDate(value: string) {
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? "Date unavailable"
      : date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  }

  function formatMoney(value: string | number, currency: string) {
    return `${currency === "INR" ? "₹" : currency + " "}${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  }

  function toggleWishlist(id: string) {
    setWishlist((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id],
    );
  }

  return (
    <div className="site-shell">
      <div className="announcement-bar">
        <span><Truck size={14} /> Free shipping on orders over ₹999</span>
        <span className="announcement-center">
          <Leaf size={14} /> Fresh food. Happier tails.
        </span>
        <span>Made for your best friend <span className="tiny-heart">♥</span></span>
      </div>

      <header className="site-header">
        <button
          className="icon-button mobile-menu-button"
          aria-label="Toggle navigation"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X /> : <Menu />}
        </button>

        <a className="brand" href="#home" aria-label="Paw Pantry home">
          <span className="brand-mark"><PawPrint size={28} /></span>
          <span className="brand-copy">
            <strong>paw pantry<span>.</span></strong>
            <small>GOOD FOOD. HAPPY PAWS.</small>
          </span>
        </a>

        <nav className={`main-nav ${mobileMenuOpen ? "nav-open" : ""}`}>
          <a className="nav-active" href="#home">Home</a>
          <a href="#shop">Shop <ChevronDown size={13} /></a>
          <a href="#categories">Dog Food</a>
          <a href="#categories">Life Stages</a>
          <a href="#why-us">Our Story</a>
          <a href="#footer">Feeding Guide</a>
        </nav>

        <div className="header-actions">
          <label className="header-search" aria-label="Search products">
            <Search size={17} />
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                document.getElementById("shop")?.scrollIntoView({
                  behavior: "smooth",
                });
              }}
              placeholder="Search..."
            />
          </label>
          <button
            type="button"
            className="button button-outline"
            aria-label={isLoggedIn ? "Log out of Paw Pantry" : "Log in to Paw Pantry"}
            onClick={() => {
              if (isLoggedIn) {
                handleLogout();
              } else {
                setLoginOpen(true);
              }
            }}
            style={{ padding: "10px 14px", whiteSpace: "nowrap", minHeight: 40 }}
          >
            {isLoggedIn ? "Log out" : "Log in"}
          </button>
          
          {isLoggedIn && (
            <button
              type="button"
              className="button button-outline"
              onClick={() => void openMyOrders()}
              style={{ padding: "10px 14px", whiteSpace: "nowrap", minHeight: 40 }}
            >
              My Orders
            </button>
          )}
          <button
            className="icon-button cart-button"
            aria-label={`Cart, ${cart?.items.reduce((total, item) => total + item.quantity, 0) ?? 0} items`}
            onClick={() => {
              setCartOpen(true);
              if (isLoggedIn) void refreshCart();
              else setNotice("Please log in to view your shopping cart.");
            }}
          >
          <ShoppingBag size={21} />
          <span className="cart-badge">
          {cart?.items.reduce((total, item) => total + item.quantity, 0) ?? 0}
          </span>
        </button>
        </div>
      </header>

      {loginOpen && (
        <div
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) setLoginOpen(false);
          }}
          style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(22, 35, 27, 0.48)", display: "grid", placeItems: "center", padding: 20 }}
        >
          <section role="dialog" aria-modal="true" aria-labelledby="login-title" style={{ width: "min(100%, 420px)", background: "#fffaf3", borderRadius: 24, padding: 28, boxShadow: "0 24px 80px rgba(0,0,0,.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
              <div>
                <span className="eyebrow">WELCOME BACK</span>
                <h2 id="login-title" style={{ margin: "8px 0 4px" }}>Your happy-paws account</h2>
                <p style={{ margin: 0, color: "#687568" }}>Log in to access your shopping cart.</p>
              </div>
              <button className="icon-button" aria-label="Close login" onClick={() => setLoginOpen(false)}><X size={18} /></button>
            </div>
            <form onSubmit={handleLogin} style={{ display: "grid", gap: 14, marginTop: 24 }}>
              <label style={{ display: "grid", gap: 6, fontWeight: 600 }}>
                Email address
                <input type="email" required autoComplete="email" value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} placeholder="you@example.com" style={{ width: "100%", boxSizing: "border-box", border: "1px solid #d8dfd1", borderRadius: 12, padding: "12px 14px", background: "white" }} />
              </label>
              <label style={{ display: "grid", gap: 6, fontWeight: 600 }}>
                Password
                <input type="password" required autoComplete="current-password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} placeholder="Your password" style={{ width: "100%", boxSizing: "border-box", border: "1px solid #d8dfd1", borderRadius: 12, padding: "12px 14px", background: "white" }} />
              </label>
              <button className="button button-dark" type="submit" disabled={cartLoading}>{cartLoading ? "Signing in..." : "Log in to Paw Pantry"}</button>
              {isLoggedIn && <button className="button button-outline" type="button" onClick={handleLogout}>Log out</button>}
            </form>
          </section>
        </div>
      )}


      {ordersOpen && (
        <div
          role="presentation"
          onClick={(event) => { if (event.target === event.currentTarget) setOrdersOpen(false); }}
          style={{ position: "fixed", inset: 0, zIndex: 1001, background: "rgba(22, 35, 27, 0.5)", display: "grid", placeItems: "center", padding: 16 }}
        >
          <section role="dialog" aria-modal="true" aria-labelledby="orders-title" style={{ width: "min(100%, 850px)", maxHeight: "90vh", overflowY: "auto", boxSizing: "border-box", background: "#fffaf3", borderRadius: 24, padding: "clamp(20px, 4vw, 32px)", boxShadow: "0 24px 80px rgba(0,0,0,.22)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, borderBottom: "1px solid #e4e8df", paddingBottom: 18 }}>
              <div>
                <span className="eyebrow">YOUR PAW PANTRY ACCOUNT</span>
                <h2 id="orders-title" style={{ margin: "8px 0 4px", color: "#234c3a" }}>My Orders</h2>
                <p style={{ margin: 0, color: "#687568" }}>All your good things, in one place.</p>
              </div>
              <button className="icon-button" aria-label="Close my orders" onClick={() => setOrdersOpen(false)}><X /></button>
            </div>

            {ordersLoading ? (
              <p role="status" style={{ padding: 24, textAlign: "center" }}>Loading your orders...</p>
            ) : ordersError ? (
              <div role="alert" style={{ marginTop: 20, padding: 16, background: "#fbe9e4", color: "#923c2c", borderRadius: 12 }}>
                <p>{ordersError}</p>
                <button className="button button-dark" onClick={() => void openMyOrders()}>Try again</button>
              </div>
            ) : orders.length === 0 ? (
              <div style={{ padding: "42px 12px", textAlign: "center" }}>
                <span style={{ fontSize: 42 }}>🐾</span>
                <h3>No orders yet</h3>
                <p style={{ color: "#687568" }}>Your next favourite for your pup is just around the corner.</p>
                <button className="button button-dark" onClick={() => { setOrdersOpen(false); document.getElementById("shop")?.scrollIntoView({ behavior: "smooth" }); }}>Explore products</button>
              </div>
            ) : (
              <div style={{ display: "grid", gap: 16, marginTop: 20 }}>
                {orders.map((order) => (
                  <article key={order.id} style={{ border: "1px solid #e0e6dc", borderRadius: 16, padding: "18px", background: "#fffdf9" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                      <div>
                        <strong style={{ color: "#234c3a", fontSize: 17 }}>Order {order.order_number}</strong>
                        <p style={{ margin: "5px 0 0", color: "#687568", fontSize: 13 }}>Placed on {formatOrderDate(order.created_at)}</p>
                      </div>
                      <span style={{ display: "inline-block", borderRadius: 999, background: "#e2e9d7", color: "#285c45", padding: "6px 11px", fontSize: 12, fontWeight: 700, textTransform: "capitalize" }}>{String(order.status).replaceAll("_", " ")}</span>
                    </div>
                    <div style={{ display: "grid", gap: 10, margin: "16px 0" }}>
                      {order.items.map((item) => (
                        <div key={item.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "#3c4b3e" }}>
                          <span>{item.name_snapshot} <span style={{ color: "#687568" }}>× {item.quantity}</span></span>
                          <strong style={{ whiteSpace: "nowrap" }}>{formatMoney(Number(item.unit_price) * item.quantity, order.currency)}</strong>
                        </div>
                      ))}
                    </div>
                    <div style={{ borderTop: "1px solid #e4e8df", paddingTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                      <span style={{ color: "#687568", fontSize: 13 }}>{order.items.length} item type{order.items.length === 1 ? "" : "s"}</span>
                      <span style={{ fontSize: 17, fontWeight: 800, color: "#234c3a" }}>Total: {formatMoney(order.total_amount, order.currency)}</span>
                    </div>
                    <div style={{ marginTop: 14 }}>
                      <button className="button button-outline" type="button" onClick={() => void loadOrderDetail(order.id)}>
                        View details &amp; tracking
                      </button>
                    </div>
                    {orderDetail?.id === order.id && (
                      <section aria-label={`Tracking for order ${order.order_number}`} style={{ marginTop: 16, padding: 16, borderRadius: 12, background: "#f3f6ee", border: "1px solid #dce5d5" }}>
                        <h3 style={{ margin: "0 0 12px", color: "#234c3a" }}>Order details &amp; tracking</h3>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16 }}>
                          <div><span style={{ color: "#687568", fontSize: 12 }}>Subtotal</span><div><strong>{formatMoney(orderDetail.subtotal_amount, orderDetail.currency)}</strong></div></div>
                          <div><span style={{ color: "#687568", fontSize: 12 }}>Shipping</span><div><strong>{formatMoney(orderDetail.shipping_amount, orderDetail.currency)}</strong></div></div>
                          <div><span style={{ color: "#687568", fontSize: 12 }}>Tax</span><div><strong>{formatMoney(orderDetail.tax_amount, orderDetail.currency)}</strong></div></div>
                          <div><span style={{ color: "#687568", fontSize: 12 }}>Discount</span><div><strong>{formatMoney(orderDetail.discount_amount, orderDetail.currency)}</strong></div></div>
                        </div>
                        <h4 style={{ margin: "12px 0 8px", color: "#234c3a" }}>Shipping address</h4>
                        <p style={{ margin: 0, color: "#3c4b3e" }}>{Object.values(orderDetail.shipping_address_snapshot).filter((value) => typeof value === "string" || typeof value === "number").join(", ") || "Address snapshot unavailable"}</p>
                        <h4 style={{ margin: "16px 0 8px", color: "#234c3a" }}>Shipment</h4>
                        {orderDetail.shipments.length === 0 ? (
                          <p style={{ margin: 0, color: "#687568" }}>Shipment tracking will appear here once your order is dispatched.</p>
                        ) : orderDetail.shipments.map((shipment) => (
                          <div key={shipment.id} style={{ marginBottom: 10, padding: 12, background: "#fffdf9", borderRadius: 10 }}>
                            <p style={{ margin: 0 }}><strong>Status:</strong> <span style={{ textTransform: "capitalize" }}>{shipment.status.replaceAll("_", " ")}</span></p>
                            {shipment.carrier && <p style={{ margin: "5px 0 0" }}><strong>Carrier:</strong> {shipment.carrier}</p>}
                            {shipment.tracking_number && <p style={{ margin: "5px 0 0" }}><strong>Tracking number:</strong> {shipment.tracking_number}</p>}
                            {shipment.shipped_at && <p style={{ margin: "5px 0 0" }}><strong>Shipped:</strong> {formatOrderDate(shipment.shipped_at)}</p>}
                            {shipment.delivered_at && <p style={{ margin: "5px 0 0" }}><strong>Delivered:</strong> {formatOrderDate(shipment.delivered_at)}</p>}
                          </div>
                        ))}
                        <h4 style={{ margin: "16px 0 8px", color: "#234c3a" }}>Status timeline</h4>
                        {orderDetail.status_history.length === 0 ? (
                          <p style={{ margin: 0, color: "#687568" }}>No status updates have been recorded yet.</p>
                        ) : (
                          <ol style={{ margin: 0, paddingLeft: 20, display: "grid", gap: 10 }}>
                            {orderDetail.status_history.map((event) => (
                              <li key={event.id}>
                                <strong style={{ textTransform: "capitalize" }}>{event.new_status.replaceAll("_", " ")}</strong>
                                <div style={{ fontSize: 12, color: "#687568" }}>{new Date(event.created_at).toLocaleString("en-IN")}</div>
                                {event.reason && <div style={{ color: "#3c4b3e" }}>{event.reason}</div>}
                              </li>
                            ))}
                          </ol>
                        )}
                      </section>
                    )}
                    {orderDetailLoading && <p role="status" style={{ marginTop: 12 }}>Loading order details…</p>}
                    {orderDetailError && <p role="alert" style={{ marginTop: 12, color: "#923c2c" }}>{orderDetailError}</p>}
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {cartOpen && (
        <div
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget) setCartOpen(false);
          }}
          style={{ position: "fixed", inset: 0, zIndex: 999, background: "rgba(22, 35, 27, 0.42)", display: "flex", justifyContent: "flex-end" }}
        >
          <aside aria-label="Shopping cart" style={{ width: "min(100%, 460px)", height: "100%", overflowY: "auto", boxSizing: "border-box", background: "#fffaf3", padding: 24, boxShadow: "-16px 0 50px rgba(0,0,0,.14)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, borderBottom: "1px solid #e4e8df", paddingBottom: 18 }}>
              <div><span className="eyebrow">PAW PANTRY</span><h2 style={{ margin: "6px 0 0" }}>Your cart</h2></div>
              <button className="icon-button" aria-label="Close cart" onClick={() => setCartOpen(false)}><X /></button>
            </div>
            {!isLoggedIn ? (
              <div style={{ padding: "36px 4px", textAlign: "center" }}>
                <ShoppingBag size={38} /><h3>Please log in first</h3>
                <p>Your cart is linked to your account so it can be saved between visits.</p>
                <button className="button button-dark" onClick={() => { setCartOpen(false); setLoginOpen(true); }}>Log in</button>
              </div>
            ) : cartLoading && !cart ? (
              <p role="status" style={{ padding: 24 }}>Loading your cart...</p>
            ) : !cart || cart.items.length === 0 ? (
              <div style={{ padding: "36px 4px", textAlign: "center" }}>
                <ShoppingBag size={38} /><h3>Your cart is waiting for a little love</h3>
                <p>Add your dog's favourites and they'll appear here.</p>
                <button className="button button-dark" onClick={() => setCartOpen(false)}>Continue shopping</button>
              </div>
            ) : (
              <>
                <div style={{ display: "grid", gap: 16, padding: "20px 0" }}>
                  {cart.items.map((item) => (
                    <article key={item.id} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 12, paddingBottom: 16, borderBottom: "1px solid #e4e8df" }}>
                      <div>
                        <strong>{item.product_name}</strong>
                        <p style={{ margin: "5px 0", color: "#687568" }}>{item.variant_name}{item.weight_grams ? ` · ${item.weight_grams} g` : ""}</p>
                        <strong>{item.currency} {Number(item.unit_price).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</strong>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
                          <button className="icon-button" aria-label={`Decrease ${item.product_name} quantity`} disabled={cartLoading || item.quantity <= 1} onClick={() => void changeCartQuantity(item.id, item.quantity - 1)}>−</button>
                          <span aria-label="Quantity">{item.quantity}</span>
                          <button className="icon-button" aria-label={`Increase ${item.product_name} quantity`} disabled={cartLoading || item.quantity >= 100} onClick={() => void changeCartQuantity(item.id, item.quantity + 1)}>+</button>
                          <button type="button" onClick={() => void deleteCartItem(item.id)} disabled={cartLoading} style={{ border: 0, background: "transparent", color: "#a34b36", textDecoration: "underline", cursor: "pointer", marginLeft: 4 }}>Remove</button>
                        </div>
                      </div>
                      <strong>{item.currency} {(Number(item.unit_price) * item.quantity).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</strong>
                    </article>
                  ))}
                </div>
                <div style={{ borderTop: "1px solid #d8dfd1", paddingTop: 18 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 18, fontWeight: 700 }}><span>Subtotal</span><span>{cart.currency} {Number(cart.subtotal).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span></div>
                  <p style={{ color: "#687568", fontSize: 13 }}>Shipping and taxes are calculated at checkout.</p>
                  <button className="button button-dark" style={{ width: "100%" }} onClick={() => void openCheckout()} disabled={cartLoading}>Proceed to checkout <ArrowRight size={16} /></button>
                </div>
              </>
            )}
          </aside>
        </div>
      )}

      {checkoutOpen && (
        <div
          role="presentation"
          onClick={(event) => {
            if (event.target === event.currentTarget && !checkoutLoading) setCheckoutOpen(false);
          }}
          style={{ position: "fixed", inset: 0, zIndex: 1001, overflowY: "auto", background: "rgba(22, 35, 27, 0.55)", padding: 20, display: "grid", placeItems: "start center" }}
        >
          <section role="dialog" aria-modal="true" aria-labelledby="checkout-title" style={{ width: "min(100%, 920px)", margin: "24px auto", background: "#fffaf3", borderRadius: 24, padding: "clamp(20px, 4vw, 36px)", boxSizing: "border-box", boxShadow: "0 24px 80px rgba(0,0,0,.22)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, borderBottom: "1px solid #e4e8df", paddingBottom: 20 }}>
              <div>
                <span className="eyebrow">PAW PANTRY · SECURE CHECKOUT</span>
                <h2 id="checkout-title" style={{ margin: "8px 0 4px", color: "#234c3a" }}>{completedOrder ? "Order confirmed!" : "Almost home for your pup."}</h2>
                <p style={{ margin: 0, color: "#687568" }}>{completedOrder ? "Thank you for choosing Paw Pantry." : "Confirm your delivery address and review your order."}</p>
              </div>
              <button className="icon-button" aria-label="Close checkout" onClick={() => setCheckoutOpen(false)} disabled={checkoutLoading}><X /></button>
            </div>

            {checkoutError && <p role="alert" style={{ marginTop: 18, padding: 12, borderRadius: 10, background: "#fbe9e4", color: "#923c2c" }}>{checkoutError}</p>}

            {completedOrder ? (
              <div style={{ padding: "36px 0 12px", textAlign: "center" }}>
                <span style={{ display: "inline-grid", placeItems: "center", width: 64, height: 64, borderRadius: "50%", background: "#e2e9d7", color: "#285c45" }}><Check size={32} /></span>
                <h3 style={{ color: "#234c3a", fontSize: 24 }}>Thank you for your order!</h3>
                <p style={{ color: "#687568" }}>Order number</p>
                <strong style={{ fontSize: 22 }}>{completedOrder.order_number}</strong>
                <p style={{ color: "#687568" }}>Status: {completedOrder.status}</p>
                <div style={{ display: "flex", justifyContent: "center", gap: 12, flexWrap: "wrap", marginTop: 24 }}>
                  <button className="button button-dark" onClick={() => setCheckoutOpen(false)}>Continue shopping</button>
                  <button className="button button-outline" onClick={() => { setCompletedOrder(null); setCheckoutOpen(false); }}>Close</button>
                </div>
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 28, paddingTop: 24 }}>
                <div>
                  <h3 style={{ marginTop: 0, color: "#234c3a" }}>1. Shipping address</h3>
                  {checkoutLoading && addresses.length === 0 ? <p>Loading your saved addresses...</p> : (
                    <>
                      {addresses.length > 0 && !addressFormOpen && (
                        <div style={{ display: "grid", gap: 12 }}>
                          {addresses.map((address) => (
                            <label key={address.id} style={{ display: "flex", gap: 12, alignItems: "flex-start", border: selectedAddressId === address.id ? "2px solid #285c45" : "1px solid #d8dfd1", borderRadius: 14, padding: 14, cursor: "pointer", background: selectedAddressId === address.id ? "#f0f4eb" : "white" }}>
                              <input type="radio" name="shipping-address" value={address.id} checked={selectedAddressId === address.id} onChange={() => setSelectedAddressId(address.id)} style={{ marginTop: 4 }} />
                              <span>
                                <strong>{address.recipient_name}</strong>{address.is_default && <span style={{ marginLeft: 8, color: "#285c45", fontSize: 12 }}>DEFAULT</span>}
                                <span style={{ display: "block", marginTop: 5, color: "#687568", lineHeight: 1.5 }}>{address.line1}{address.line2 ? `, ${address.line2}` : ""}<br />{address.city}, {address.state_region} {address.postal_code}<br />{address.country_code}{address.phone ? ` · ${address.phone}` : ""}</span>
                              </span>
                            </label>
                          ))}
                          <button className="button button-outline" type="button" onClick={() => setAddressFormOpen(true)}>+ Add another address</button>
                        </div>
                      )}

                      {(addressFormOpen || addresses.length === 0) && (
                        <form onSubmit={saveAddress} style={{ display: "grid", gap: 12 }}>
                          <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>Recipient name
                            <input required maxLength={160} value={addressForm.recipient_name} onChange={(event) => setAddressForm({ ...addressForm, recipient_name: event.target.value })} placeholder="Full name" style={checkoutInputStyle} />
                          </label>
                          <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>Phone
                            <input type="tel" maxLength={32} value={addressForm.phone} onChange={(event) => setAddressForm({ ...addressForm, phone: event.target.value })} placeholder="Phone number" style={checkoutInputStyle} />
                          </label>
                          <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>Address line 1
                            <input required maxLength={255} value={addressForm.line1} onChange={(event) => setAddressForm({ ...addressForm, line1: event.target.value })} placeholder="House number, street, area" style={checkoutInputStyle} />
                          </label>
                          <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>Address line 2 (optional)
                            <input maxLength={255} value={addressForm.line2} onChange={(event) => setAddressForm({ ...addressForm, line2: event.target.value })} placeholder="Apartment, landmark" style={checkoutInputStyle} />
                          </label>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
                            <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>City
                              <input required maxLength={120} value={addressForm.city} onChange={(event) => setAddressForm({ ...addressForm, city: event.target.value })} style={checkoutInputStyle} />
                            </label>
                            <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>State
                              <input required maxLength={120} value={addressForm.state_region} onChange={(event) => setAddressForm({ ...addressForm, state_region: event.target.value })} style={checkoutInputStyle} />
                            </label>
                          </div>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 10 }}>
                            <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>Postal code
                              <input required maxLength={24} value={addressForm.postal_code} onChange={(event) => setAddressForm({ ...addressForm, postal_code: event.target.value })} style={checkoutInputStyle} />
                            </label>
                            <label style={{ display: "grid", gap: 5, fontWeight: 600 }}>Country code
                              <input required minLength={2} maxLength={2} value={addressForm.country_code} onChange={(event) => setAddressForm({ ...addressForm, country_code: event.target.value.toUpperCase() })} style={checkoutInputStyle} />
                            </label>
                          </div>
                          <label style={{ display: "flex", gap: 8, alignItems: "center", fontWeight: 500 }}><input type="checkbox" checked={addressForm.is_default} onChange={(event) => setAddressForm({ ...addressForm, is_default: event.target.checked })} /> Save as my default shipping address</label>
                          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                            <button className="button button-dark" type="submit" disabled={addressSaving}>{addressSaving ? "Saving address..." : "Save address"}</button>
                            {addresses.length > 0 && <button className="button button-outline" type="button" onClick={() => setAddressFormOpen(false)}>Cancel</button>}
                          </div>
                        </form>
                      )}
                    </>
                  )}
                </div>

                <div>
                  <h3 style={{ marginTop: 0, color: "#234c3a" }}>2. Order summary</h3>
                  <div style={{ border: "1px solid #e0e5da", borderRadius: 16, padding: 18, background: "white" }}>
                    <div style={{ display: "grid", gap: 14 }}>
                      {cart?.items.map((item) => (
                        <div key={item.id} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                          <span><strong>{item.product_name}</strong><span style={{ display: "block", fontSize: 13, color: "#687568" }}>{item.variant_name} · Qty {item.quantity}</span></span>
                          <strong style={{ whiteSpace: "nowrap" }}>{item.currency} {(Number(item.unit_price) * item.quantity).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</strong>
                        </div>
                      ))}
                    </div>
                    <div style={{ borderTop: "1px solid #e4e8df", marginTop: 18, paddingTop: 16, display: "grid", gap: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}><span>Subtotal</span><span>{cart?.currency ?? "INR"} {Number(cart?.subtotal ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between", color: "#687568" }}><span>Shipping</span><span>₹0.00</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between", color: "#687568" }}><span>Tax</span><span>₹0.00</span></div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 18, fontWeight: 800, borderTop: "1px solid #e4e8df", paddingTop: 12 }}><span>Total</span><span>{cart?.currency ?? "INR"} {Number(cart?.subtotal ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span></div>
                    </div>
                    <p style={{ color: "#687568", fontSize: 12, lineHeight: 1.5 }}>Shipping and tax are currently set to ₹0 by the checkout backend.</p>
                    <button className="button button-dark" style={{ width: "100%", marginTop: 12 }} onClick={() => void placeOrder()} disabled={checkoutLoading || addressSaving || addresses.length === 0 || !selectedAddressId}>
                      {checkoutLoading ? "Placing order..." : "Place order"} <ArrowRight size={16} />
                    </button>
                    <p style={{ fontSize: 12, color: "#687568", textAlign: "center" }}><ShieldCheck size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />Your order is processed securely.</p>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      <main>
        <section className="hero-section" id="home">
          <div className="hero-copy">
            <span className="eyebrow"><PawPrint size={15} /> GOODNESS IN EVERY BITE</span>
            <h1>
              Healthy Food.
              <br />
              Happier <span className="title-highlight">Tails.</span>
            </h1>
            <p>
              Nutritious meals for every stage of your dog's life.
              Feel-good ingredients, real nourishment, more tail wags.
            </p>
            <div className="hero-buttons">
              <a className="button button-orange" href="#shop">
                Shop Now <ArrowRight size={16} />
              </a>
              <a className="button button-outline" href="#why-us">
                Learn More
              </a>
            </div>
            <div className="hero-trust">
              <span><Check size={15} /> Vet approved</span>
              <span><Check size={15} /> Real ingredients</span>
            </div>
          </div>

          <div className="hero-image">
            <img
              src="https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=1200&q=85"
              alt="Happy golden retriever enjoying life outdoors"
            />
            <div className="hero-image-wash" />
            <div className="hero-note">
              Good Food,
              <br />
              Brighter Days <span>♡</span>
            </div>
            <div className="hero-sticker">
              <PawPrint size={18} />
              <span>Made with<br />love & care</span>
            </div>
          </div>
          <div className="hero-bottom-label">NOURISH THEIR WORLD. ONE BOWL AT A TIME.</div>
        </section>

        <section className="benefit-strip" id="why-us">
          <div><span className="benefit-icon"><Leaf /></span><span><strong>Natural Ingredients</strong><small>Nothing unnecessary</small></span></div>
          <div><span className="benefit-icon"><ShieldCheck /></span><span><strong>Vet Approved</strong><small>Nutrition you can trust</small></span></div>
          <div><span className="benefit-icon"><PawPrint /></span><span><strong>No Artificial Additives</strong><small>Only the good stuff</small></span></div>
          <div><span className="benefit-icon"><Heart /></span><span><strong>Happier Dogs</strong><small>Happy from the inside</small></span></div>
        </section>

        <section className="content-section categories-section" id="categories">
          <div className="section-heading">
            <div>
              <span className="eyebrow">A LITTLE SOMETHING FOR EVERY PAW</span>
              <h2>Shop by Category<span className="heading-dot">.</span></h2>
            </div>
            <a className="text-link" href="#shop">Explore all <ArrowRight size={16} /></a>
          </div>

          <div className="category-grid">
            {categories.map((category) => (
              <button
                className={`category-card ${activeCategory === category.name ? "category-selected" : ""}`}
                key={category.name}
                onClick={() => {
                  setActiveCategory(
                    activeCategory === category.name ? "All" : category.name,
                  );
                  document.getElementById("shop")?.scrollIntoView({
                    behavior: "smooth",
                  });
                }}
              >
                <span className="category-art" style={{ backgroundColor: category.color }}>
                  <span>{category.icon}</span>
                </span>
                <strong>{category.name}</strong>
                <span className="category-arrow"><ArrowRight size={15} /></span>
              </button>
            ))}
          </div>
        </section>

        <section className="content-section featured-section" id="shop">
          <div className="section-heading">
            <div>
              <span className="eyebrow">GOOD FOOD, GREAT MOOD</span>
              <h2>{search ? "Search Results" : "Featured Products"}<span className="heading-dot">.</span></h2>
              <p className="section-description">
                {search
                  ? `Showing matches for "${search}"`
                  : "Thoughtfully made favourites your dog will love."}
              </p>
            </div>
            <div className="product-section-actions">
              <button
                className={`filter-pill ${activeCategory === "All" ? "filter-active" : ""}`}
                onClick={() => setActiveCategory("All")}
              >
                All products
              </button>
              <a className="text-link desktop-link" href="#shop">View all <ArrowRight size={16} /></a>
            </div>
          </div>

          <div className="product-grid">
            {productsLoading && (
              <div className="empty-state" role="status">
                <span>🐾</span>
                <h3>Finding their favourites...</h3>
                <p>Loading fresh picks from Paw Pantry.</p>
              </div>
            )}
            {!productsLoading && productsError && (
              <div className="empty-state" role="alert">
                <span>🐾</span>
                <h3>We couldn't load the products</h3>
                <p>{productsError}. Make sure the Paw Pantry API is running.</p>
                <button className="button button-dark" onClick={() => window.location.reload()}>
                  Try again
                </button>
              </div>
            )}
            {!productsLoading && !productsError && filteredProducts.map((product) => (
              <article className="product-card" key={product.id}>
                <div className="product-visual">
                  {product.tag && <span className="product-tag">{product.tag}</span>}
                  <button
                    className={`wishlist-button ${wishlist.includes(product.id) ? "wishlisted" : ""}`}
                    aria-label={wishlist.includes(product.id) ? "Remove from wishlist" : "Add to wishlist"}
                    onClick={() => toggleWishlist(product.id)}
                  >
                    <Heart size={18} fill={wishlist.includes(product.id) ? "currentColor" : "none"} />
                  </button>
                  <ProductPack product={product} />
                </div>
                <div className="product-info">
                  <span className="product-category">{product.category}</span>
                  <h3>{product.name}</h3>
                  <div className="product-rating">
                    <span className="stars"><Star size={13} fill="currentColor" /> {product.rating}</span>
                    <span className="rating-count">(120+ reviews)</span>
                  </div>
                  <div className="product-price-row">
                    <strong>₹{product.price.toLocaleString("en-IN")}</strong>
                    <span>{product.size}</span>
                  </div>
                  <button className="button button-dark add-button" disabled={cartLoading} onClick={() => void addToCart(product)}>
                    Add to Cart <ShoppingBag size={15} />
                  </button>
                </div>
              </article>
            ))}
            {!productsLoading && !productsError && filteredProducts.length === 0 && (
              <div className="empty-state">
                <span>🐾</span>
                <h3>No matching products just yet</h3>
                <p>Try another search or explore all our favourites.</p>
                <button className="button button-dark" onClick={() => {
                  setSearch("");
                  setActiveCategory("All");
                }}>Show all products</button>
              </div>
            )}
          </div>
        </section>

        <section className="story-banner">
          <div className="story-illustration"><span>🌱</span><span>🐾</span></div>
          <div>
            <span className="eyebrow">A LITTLE MORE LOVE IN EVERY MEAL</span>
            <h2>Because they're family, too.</h2>
            <p>Good ingredients. Thoughtful nutrition. More years of doing everything together.</p>
          </div>
          <a href="#why-us" className="button button-orange">Our Story <ArrowRight size={16} /></a>
        </section>

        <section className="newsletter-section">
          <div className="newsletter-paw"><PawPrint size={25} /></div>
          <div>
            <span className="eyebrow">LET'S STAY IN TOUCH</span>
            <h2>A happier inbox. A happier pup.</h2>
            <p>Get feeding tips, new favourites and little surprises.</p>
          </div>
          <form className="newsletter-form" onSubmit={(event) => {
            event.preventDefault();
            setNotice("Thanks for joining our happy-paws club!");
          }}>
            <input type="email" required placeholder="Your email address" aria-label="Email address" />
            <button type="submit" className="button button-dark">Join the pack <ArrowRight size={15} /></button>
          </form>
        </section>
      </main>

      <footer className="site-footer" id="footer">
        <a className="brand footer-brand" href="#home">
          <span className="brand-mark"><PawPrint size={27} /></span>
          <span className="brand-copy"><strong>paw pantry<span>.</span></strong><small>GOOD FOOD. HAPPY PAWS.</small></span>
        </a>
        <p>Made with love for the ones who make life better. <span>♥</span></p>
        <div className="footer-links"><a href="#shop">Shop</a><a href="#why-us">Our Story</a><a href="#footer">Contact</a><a href="#footer">Privacy</a></div>
        <small className="copyright">© 2026 Paw Pantry. All paws reserved.</small>
      </footer>

      {notice && (
        <div className="toast" role="status">
          <Check size={18} />
          <span>{notice}</span>
          <button aria-label="Dismiss notification" onClick={() => setNotice("")}><X size={16} /></button>
        </div>
      )}
    </div>
  );
}

export default App;
