"use client";

import React, {
  useState,
  useEffect,
  useCallback,
  createContext,
  useContext,
  useMemo,
} from "react";
import {
  User,
  LoginCredentials,
  login,
  logout,
  getCurrentUser,
  register,
  RegisterData,
} from "@/utils/auth";

type AuthContextType = {
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

// Create context with default values
export const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  error: null,
  isAuthenticated: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshUser: async () => {},
});

// Hook to use the auth context
export function useAuth() {
  return useContext(AuthContext);
}

// Provider component
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch current user data
  const refreshUser = useCallback(async () => {
    try {
      setLoading(true);
      const userData = await getCurrentUser();
      setUser(userData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch user");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Check if user is authenticated
  const isAuthenticated = !!user;

  // Handle loginrefreshUser
  const handleLogin = useCallback(async (credentials: LoginCredentials) => {
    try {
      setLoading(true);
      setError(null);
      await login(credentials);
      await refreshUser();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      throw err;
    } finally {
      setLoading(false);
    }
    }, [refreshUser]);

  // Handle register
  const handleRegister = useCallback(async (data: RegisterData) => {
    try {
      setLoading(true);
      setError(null);
      await register(data);
      // Automatically log in after registration
      await login({ username: data.username, password: data.password });
      await refreshUser();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      throw err;
    } finally {
      setLoading(false);
    }
  }, [refreshUser]);

  // Handle logout
  const handleLogout = () => {
    logout();
    setUser(null);
  };

  // Check authentication status when component mounts
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      isAuthenticated,
      login: handleLogin,
      register: handleRegister,
      logout: handleLogout,
      refreshUser,
    }),
    [user, loading, error, isAuthenticated, handleLogin, handleRegister, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
