import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "../services/api";

export interface User {
  id: number;
  name: string;
  email: string;
  phone?: string | null;
  role: string;
  is_active?: boolean;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
  phone?: string;
}

type AuthStatus = "loading" | "authenticated" | "guest";

interface AuthContextType {
  user: User | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const clearSession = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  const refreshUser = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setUser(null);
      setStatus("guest");
      return;
    }
    try {
      const response = await api.get<User>("/api/auth/me");
      setUser(response.data);
      setStatus("authenticated");
    } catch {
      clearSession();
      setStatus("guest");
    }
  };

  useEffect(() => {
    void refreshUser();
  }, []);

  const login = async (email: string, password: string) => {
    const formData = new FormData();
    formData.append("username", email);
    formData.append("password", password);
    const response = await api.post<{ access_token: string }>(
      "/api/auth/login",
      formData
    );
    localStorage.setItem("token", response.data.access_token);
    await refreshUser();
  };

  const register = async (data: RegisterData) => {
    await api.post("/api/auth/register", data);
    await login(data.email, data.password);
  };

  const logout = () => {
    clearSession();
    setStatus("guest");
  };

  return (
    <AuthContext.Provider value={{ user, status, login, register, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}