/**
 * 인증 API 클라이언트
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface User {
  userId: string;
  email: string;
  name: string;
  orgId: string;
  role: string;
  avatarUrl?: string;
}

export interface LoginResponse {
  accessToken: string;
  tokenType: string;
  user: User;
}

export async function signup(email: string, name: string, password: string, orgName?: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, password, org_name: orgName }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to sign up: ${response.statusText}`);
  }
  return response.json();
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to login: ${response.statusText}`);
  }
  return response.json();
}

export async function logout(token: string): Promise<void> {
  await fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`Failed to get user: ${response.statusText}`);
  }
  return response.json();
}

export interface UpdateProfileRequest {
  name?: string;
  email?: string;
}

export async function updateProfile(token: string, data: UpdateProfileRequest): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/auth/profile`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to update profile: ${response.statusText}`);
  }
  return response.json();
}

export async function changePassword(
  token: string,
  currentPassword: string,
  newPassword: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/password`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to change password: ${response.statusText}`);
  }
}

export interface ContactRequest {
  subject: string;
  message: string;
}

export async function submitContactForm(token: string, data: ContactRequest): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/support/contact`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to submit contact form: ${response.statusText}`);
  }
}
