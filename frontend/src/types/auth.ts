export interface UserProfile {
  id: string;
  username: string;
  name: string;
  email: string;
  role: string;
  avatar_url?: string;
}

export interface AuthResponse {
  token: string;
  user: UserProfile;
}

