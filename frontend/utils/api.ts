/**
 * API utilities for making requests to the backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ApiResponse<T> = {
  data?: T;
  error?: string;
  status: number;
};

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const url = `${API_URL}${
      endpoint.startsWith("/") ? endpoint : `/${endpoint}`
    }`;

    // Default options
    const defaultHeaders: HeadersInit = {
      "Content-Type": "application/json",
    };

    // Add auth token if available
    const token =
      typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
    if (token) {
      defaultHeaders["Authorization"] = `Bearer ${token}`;
    }

    // Merge options
    const fetchOptions: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    const response = await fetch(url, fetchOptions);
    const status = response.status;

    // Handle JSON response
    const contentType = response.headers.get("content-type");
    let data;

    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (status >= 400) {
      return {
        error: data.detail || data.message || "An error occurred",
        status,
      };
    }

    return { data, status };
  } catch (error) {
    console.error("API request failed:", error);
    return {
      error: error instanceof Error ? error.message : "Unknown error",
      status: 500,
    };
  }
}

export async function get<T>(
  endpoint: string,
  params?: Record<string, string>
): Promise<ApiResponse<T>> {
  let url = endpoint;

  // Add query parameters if provided
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, value);
      }
    });

    const queryString = searchParams.toString();
    if (queryString) {
      url = `${url}${url.includes("?") ? "&" : "?"}${queryString}`;
    }
  }

  return fetchApi<T>(url, { method: "GET" });
}

export async function post<T>(
  endpoint: string,
  data?: any
): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  });
}

export async function put<T>(
  endpoint: string,
  data?: any
): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, {
    method: "PUT",
    body: data ? JSON.stringify(data) : undefined,
  });
}

export async function del<T>(endpoint: string): Promise<ApiResponse<T>> {
  return fetchApi<T>(endpoint, { method: "DELETE" });
}
