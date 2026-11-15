import type { AuthResponse, UserProfile } from "../types/auth";

const TOKEN_KEY = "crb_auth_token";
const USER_KEY = "crb_auth_user";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): UserProfile | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    return null;
  }
}

export async function loginUser(username: string, password: string): Promise<UserProfile> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    let msg = "Invalid login credentials";
    try {
      const data = await res.json();
      if (data?.detail) msg = String(data.detail);
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  const data = (await res.json()) as AuthResponse;
  localStorage.setItem(TOKEN_KEY, data.token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  return data.user;
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch("/api/auth/me", { headers });
  if (!res.ok) {
    throw new Error("Failed to fetch user");
  }
  const user = (await res.json()) as UserProfile;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

export async function logoutUser(): Promise<void> {
  const token = getStoredToken();
  try {
    if (token) {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  } catch {
    // ignore
  } finally {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
}

