import { api } from '@/lib/api';
import { User } from '@/lib/types';

export async function getCurrentUser(): Promise<User | null> {
  try {
    return await api.get<User>('/auth/me');
  } catch {
    return null;
  }
}
