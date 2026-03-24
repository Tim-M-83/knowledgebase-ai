import clsx from 'clsx';

export function cn(...values: Array<string | undefined | false>) {
  return clsx(values);
}

export function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const pairs = document.cookie.split(';').map((item) => item.trim());
  for (const pair of pairs) {
    if (pair.startsWith(`${name}=`)) {
      return decodeURIComponent(pair.split('=')[1]);
    }
  }
  return null;
}
