import { api } from "./api";
import type { AuthResponse, User } from "../types";

export const authApi = {
  login: (email: string, password: string) => api.post<AuthResponse>("/auth/login", { email, password }),
  me: () => api.get<User>("/auth/me"),
};