import { ButtonHTMLAttributes } from 'react';

import { cn } from '@/lib/utils';

type Variant = 'default' | 'secondary' | 'danger';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

export function Button({ className, variant = 'default', ...props }: Props) {
  const variantClasses: Record<Variant, string> = {
    default: 'bg-brand-500 text-white hover:bg-brand-700',
    secondary: 'bg-white text-ink border border-slate-200 hover:bg-slate-50',
    danger: 'bg-red-600 text-white hover:bg-red-700'
  };

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-2xl px-4 py-2 text-sm font-medium transition disabled:opacity-50',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}
