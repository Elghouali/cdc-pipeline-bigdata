import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { login as apiLogin } from '@/lib/api';
import type { Role, Token } from '@/types/api';

interface AuthState {
  token: string | null;
  username: string | null;
  role: Role | null;
  isAuthenticated: boolean;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = 'cdc_token';
const USER_KEY = 'cdc_user';

function loadStoredAuth(): AuthState {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const raw = localStorage.getItem(USER_KEY);
    if (token && raw) {
      const user = JSON.parse(raw) as { username: string; role: Role };
      return { token, username: user.username, role: user.role, isAuthenticated: true };
    }
  } catch {
    // ignore corrupt storage
  }
  return { token: null, username: null, role: null, isAuthenticated: false };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(loadStoredAuth);

  useEffect(() => {
    if (!auth.token) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }, [auth.token]);

  const login = useCallback(async (username: string, password: string) => {
    const token: Token = await apiLogin({ username, password });
    localStorage.setItem(TOKEN_KEY, token.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify({ username: token.username, role: token.role }));
    setAuth({
      token: token.access_token,
      username: token.username,
      role: token.role,
      isAuthenticated: true,
    });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setAuth({ token: null, username: null, role: null, isAuthenticated: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...auth, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
