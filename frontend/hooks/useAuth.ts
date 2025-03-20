import { useState, useEffect, createContext, useContext } from "react";

type User = {
  id: string;
  username: string;
  email: string;
  full_name?: string;
};

type LoginCredentials = {
  username: string;
  password: string;
};

type RegisterData = {
  username: string;
  email: string;
  password: string;
  full_name?: string;
};

type AuthContextType = {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
};

// Create context with default values
const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

// Auth provider component that wraps the app
export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // In a real app, this would be an API call to validate the token
        const storedUser = localStorage.getItem("user");
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        }
      } catch (error) {
        console.error("Authentication check failed:", error);
        localStorage.removeItem("user");
        localStorage.removeItem("token");
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    try {
      // In a real app, this would be an API call to your backend
      // Mock implementation for demo
      const mockUser: User = {
        id: "user123",
        username: credentials.username,
        email: `${credentials.username}@example.com`,
        full_name: credentials.username === "admin" ? "Admin User" : undefined,
      };

      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Validate credentials (in a real app, the server does this)
      if (credentials.password.length < 4) {
        throw new Error("Invalid credentials");
      }

      // Save user data and token
      localStorage.setItem("user", JSON.stringify(mockUser));
      localStorage.setItem("token", "mock-jwt-token");
      setUser(mockUser);
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    try {
      // In a real app, this would be an API call to your backend
      // Mock implementation for demo
      const mockUser: User = {
        id: `user${Math.floor(Math.random() * 1000)}`,
        username: data.username,
        email: data.email,
        full_name: data.full_name,
      };

      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Save user data and token
      localStorage.setItem("user", JSON.stringify(mockUser));
      localStorage.setItem("token", "mock-jwt-token");
      setUser(mockUser);
    } catch (error) {
      console.error("Registration failed:", error);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);
