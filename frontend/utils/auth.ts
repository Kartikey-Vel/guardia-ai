import { post, fetchApi } from "./api";

export type User = {
  username: string;
  email?: string;
  full_name?: string;
  id?: string;
};

export type LoginCredentials = {
  username: string;
  password: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
};

export type RegisterData = {
  username: string;
  password: string;
  email: string;
  full_name?: string;
};

// Login function
export async function login(credentials: LoginCredentials) {
  // Convert credentials to form data format required by FastAPI
  const formData = new FormData();
  formData.append("username", credentials.username);
  formData.append("password", credentials.password);

  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const response = await fetchApi<AuthResponse>("auth/token", {
      method: "POST",
      body: formData,
      headers: {
        // Don't set Content-Type for FormData
        // The browser will set the appropriate Content-Type with boundary
      },
    });

    if (response.error) {
      throw new Error(response.error);
    }

    if (!response.data) {
      throw new Error("No data received from server");
    }

    // Store the token in localStorage
    if (typeof window !== "undefined") {
      localStorage.setItem("auth_token", response.data.access_token);
    }

    return response.data;
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "Login failed");
  }
}

// Get current user function
export async function getCurrentUser(): Promise<User | null> {
  const { data, error } = await post<User>("auth/me");

  if (error || !data) {
    return null;
  }

  return data;
}

// Register function
export async function register(userData: RegisterData) {
  const { data, error } = await post<User>("auth/register", userData);

  if (error || !data) {
    throw new Error(error || "Registration failed");
  }

  return data;
}

// Logout function
export function logout() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("auth_token");
  }
}

// Check if user is authenticated
export function isAuthenticated(): boolean {
  if (typeof window !== "undefined") {
    return !!localStorage.getItem("auth_token");
  }
  return false;
}
