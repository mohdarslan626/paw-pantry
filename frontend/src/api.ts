
<<<<<<< HEAD
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "https://paw-pantry-ycnd.onrender.com/api/v1";
=======
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
>>>>>>> 8301b35 (feat: add secure image uploads and configurable API URL)

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

  return (await response.json()) as T;
}


export type UserResponse = {
  id: string;
  email: string;
  display_name: string | null;
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
