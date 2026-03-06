import { useAuthStore } from "@/store/useAuthStore";

export function useAuth() {
  const store = useAuthStore();
  return store;
}
