
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type CartItem = {
  id: string;
  variant_id: string;
  quantity: number;
  unit_price: string | number;
  currency: string;
  product_name: string;
  variant_name: string;
  weight_grams: number | null;
};

export type CartResponse = {
  id: string;
  items: CartItem[];
  subtotal: string | number;
  currency: string;
};

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("paw_pantry_access_token");

  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      body?.detail ?? `Request failed with status ${response.status}`;

    throw new Error(
      typeof message === "string" ? message : JSON.stringify(message),
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}


export type UserResponse = {
  id: string;
  email: string;
  display_name: string | null;
  roles: string[];
};

export async function loginUser(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const result = await apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  localStorage.setItem("paw_pantry_access_token", result.access_token);

  return result;
}

export type PasswordResetResponse = {
  message: string;
};

export async function requestPasswordReset(
  email: string,
): Promise<PasswordResetResponse> {
  return apiRequest<PasswordResetResponse>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<PasswordResetResponse> {
  return apiRequest<PasswordResetResponse>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({
      token,
      new_password: newPassword,
    }),
  });
}

export async function registerUser(data: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getCurrentUser(): Promise<UserResponse> {
  return apiRequest<UserResponse>("/auth/me");
}

export function logoutUser(): void {
  localStorage.removeItem("paw_pantry_access_token");
}


export async function getCart(): Promise<CartResponse> {
  return apiRequest<CartResponse>("/cart/");
}

export async function addCartItem(
  variantId: string,
  quantity = 1,
): Promise<CartResponse> {
  return apiRequest<CartResponse>("/cart/items", {
    method: "POST",
    body: JSON.stringify({
      variant_id: variantId,
      quantity,
    }),
  });
}

export async function updateCartItem(
  itemId: string,
  quantity: number,
): Promise<CartResponse> {
  return apiRequest<CartResponse>(`/cart/items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ quantity }),
  });
}

export async function removeCartItem(
  itemId: string,
): Promise<CartResponse> {
  return apiRequest<CartResponse>(`/cart/items/${itemId}`, {
    method: "DELETE",
  });
}


export type ShippingAddress = {
  id: string;
  address_type: string;
  recipient_name: string;
  phone: string | null;
  line1: string;
  line2: string | null;
  city: string;
  state_region: string;
  postal_code: string;
  country_code: string;
  is_default: boolean;
  created_at: string;
};

export type AddressCreate = {
  recipient_name: string;
  phone?: string | null;
  line1: string;
  line2?: string | null;
  city: string;
  state_region: string;
  postal_code: string;
  country_code?: string;
  is_default?: boolean;
};

export async function getAddresses(): Promise<ShippingAddress[]> {
  return apiRequest<ShippingAddress[]>("/addresses/");
}

export async function createAddress(
  address: AddressCreate,
): Promise<ShippingAddress> {
  return apiRequest<ShippingAddress>("/addresses/", {
    method: "POST",
    body: JSON.stringify(address),
  });
}

export type CheckoutRequest = {
  shipping_address_id: string;
  idempotency_key: string;
};

export type OrderItemResponse = {
  id: string;
  variant_id: string | null;
  sku_snapshot: string;
  name_snapshot: string;
  unit_price: string | number;
  quantity: number;
};

export type CheckoutResponse = {
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
  items: OrderItemResponse[];
};

export async function checkoutOrder(
  request: CheckoutRequest,
): Promise<CheckoutResponse> {
  return apiRequest<CheckoutResponse>("/orders/checkout", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

// Admin API surface
export type AdminProduct = {
  id: string; brand_id: number | null; category_id: number; name: string; slug: string;
  short_description: string | null; description: string | null; status: string;
  fulfillment_type: "internal" | "external_link"; external_url: string | null;
  external_marketplace: "amazon" | "flipkart" | "other" | null;
  created_at: string; variants: AdminVariant[]; images: AdminImage[]; ingredients: AdminProductIngredient[]; nutrition: AdminNutrition[];
};
export type AdminVariant = { id: string; sku: string; variant_name: string; weight_grams: number | null; price: string | number; currency: string; is_active: boolean };
export type AdminImage = { id: string; media_asset_id: string; alt_text: string | null; position: number; is_primary: boolean; media_asset: { id: string; object_key: string; mime_type: string; status: string; url?: string } };
export type AdminProductIngredient = { id: string; ingredient_id: number; ingredient_name: string; percentage: string | number | null; display_order: number };
export type AdminNutrition = { id: string; nutrient_code: string; value: string | number; unit: string; basis: string };
export type AdminIngredient = { id: number; name: string; description: string | null };
export type AdminCategory = { id: number; parent_id: number | null; name: string; slug: string; description: string | null; created_at: string };
export type AdminBrand = { id: number; name: string; slug: string; description: string | null; created_at: string };
export type AdminOrder = { id: string; order_number: string; status: string; currency: string; total_amount: string | number; created_at: string; items: { id: string; name_snapshot: string; quantity: number; unit_price: string | number }[] };

export const getAdminProducts = () => apiRequest<AdminProduct[]>("/products/admin?skip=0&limit=100&sort_by=created_at&sort_order=desc");
export const createAdminProduct = (data: Record<string, unknown>) => apiRequest<AdminProduct>("/products/", { method: "POST", body: JSON.stringify(data) });
export const updateAdminProduct = (id: string, data: Record<string, unknown>) => apiRequest<AdminProduct>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteAdminProduct = (id: string) => apiRequest<void>(`/products/${id}`, { method: "DELETE" });
export const getAdminIngredients = () => apiRequest<AdminIngredient[]>("/ingredients/");
export const getAdminCategories = () => apiRequest<AdminCategory[]>("/categories/");
export const saveAdminCategory = (data: Record<string, unknown>, id?: number) => apiRequest<AdminCategory>(id ? `/categories/${id}` : "/categories/", { method: id ? "PATCH" : "POST", body: JSON.stringify(data) });
export const deleteAdminCategory = (id: number) => apiRequest<void>(`/categories/${id}`, { method: "DELETE" });
export const getAdminBrands = () => apiRequest<AdminBrand[]>("/brands/");
export const saveAdminBrand = (data: Record<string, unknown>, id?: number) => apiRequest<AdminBrand>(id ? `/brands/${id}` : "/brands/", { method: id ? "PATCH" : "POST", body: JSON.stringify(data) });
export const deleteAdminBrand = (id: number) => apiRequest<void>(`/brands/${id}`, { method: "DELETE" });
export const getAdminOrders = () => apiRequest<AdminOrder[]>("/orders/admin?skip=0&limit=100");
export const createAdminVariant = (productId: string, data: Record<string, unknown>) => apiRequest<AdminVariant>(`/products/${productId}/variants/`, { method: "POST", body: JSON.stringify(data) });
export const uploadAdminImage = (file: File, onProgress?: (percent: number) => void): Promise<{ id: string; url: string }> => new Promise((resolve, reject) => {
  const token = localStorage.getItem("paw_pantry_access_token");
  const body = new FormData(); body.append("file", file);
  const xhr = new XMLHttpRequest();
  xhr.open("POST", `${API_BASE_URL}/media/images`);
  if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
  xhr.upload.onprogress = (event) => { if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100)); };
  xhr.onerror = () => reject(new Error("Image upload failed. Check your connection."));
  xhr.onload = () => {
    let data: { id?: string; url?: string; detail?: string } = {};
    try { data = JSON.parse(xhr.responseText); } catch { /* handled below */ }
    if (xhr.status < 200 || xhr.status >= 300) reject(new Error(data.detail ?? `Upload failed (${xhr.status})`));
    else resolve(data as { id: string; url: string });
  };
  xhr.send(body);
});
export const linkAdminImage = (productId: string, mediaAssetId: string, altText = "", isPrimary = false) => apiRequest<AdminImage>(`/products/${productId}/images/`, { method: "POST", body: JSON.stringify({ media_asset_id: mediaAssetId, alt_text: altText || null, is_primary: isPrimary }) });
export const updateAdminImage = (productId: string, imageId: string, data: Record<string, unknown>) => apiRequest<AdminImage>(`/products/${productId}/images/${imageId}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteAdminImage = (productId: string, imageId: string) => apiRequest<void>(`/products/${productId}/images/${imageId}`, { method: "DELETE" });
export const addAdminIngredient = (productId: string, data: Record<string, unknown>) => apiRequest<AdminProductIngredient>(`/products/${productId}/ingredients`, { method: "POST", body: JSON.stringify(data) });
export const addAdminNutrition = (productId: string, data: Record<string, unknown>) => apiRequest<AdminNutrition>(`/products/${productId}/nutrition`, { method: "POST", body: JSON.stringify(data) });

export const deleteAdminVariant = (productId: string, variantId: string) => apiRequest<void>(`/products/${productId}/variants/${variantId}`, { method: "DELETE" });
export const updateAdminVariant = (productId: string, variantId: string, data: Record<string, unknown>) => apiRequest<AdminVariant>(`/products/${productId}/variants/${variantId}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteAdminIngredient = (productId: string, id: string) => apiRequest<void>(`/products/${productId}/ingredients/${id}`, { method: "DELETE" });
export const deleteAdminNutrition = (productId: string, id: string) => apiRequest<void>(`/products/${productId}/nutrition/${id}`, { method: "DELETE" });

// Admin Inventory API
export type AdminInventoryLocation = {
  id: number;
  code: string;
  name: string;
};

export type AdminInventoryItem = {
  id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  sku: string;
  location_id: number;
  location_name: string;
  on_hand: number;
  reserved: number;
  available: number;
};

export type AdminInventoryMovement = {
  id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  sku: string;
  location_id: number;
  location_name: string;
  quantity_delta: number;
  reason: string;
  created_at: string;
};

export const getAdminInventory = () =>
  apiRequest<AdminInventoryItem[]>("/admin/inventory");

export const getAdminInventoryLocations = () =>
  apiRequest<AdminInventoryLocation[]>("/admin/inventory/locations");

export const createAdminInventoryLocation = (data: {
  code: string;
  name: string;
}) =>
  apiRequest<AdminInventoryLocation>("/admin/inventory/locations", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const adjustAdminInventory = (data: {
  variant_id: string;
  location_id: number;
  quantity_delta: number;
  reason: string;
}) =>
  apiRequest<AdminInventoryItem>("/admin/inventory/adjustments", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getAdminInventoryMovements = (variantId?: string) => {
  const query = variantId
    ? `?variant_id=${encodeURIComponent(variantId)}`
    : "";

  return apiRequest<AdminInventoryMovement[]>(
    `/admin/inventory/movements${query}`,
  );
};
