import { ReactNode } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: 'primary' | 'accent' | 'danger' | 'warning' | 'none';
}

export function GlassCard({ children, className, glowColor = 'none' }: GlassCardProps) {
  const glowMap = {
    primary: 'before:bg-[#5EEAD4]/10',
    accent: 'before:bg-[#22D3EE]/10',
    danger: 'before:bg-[#EF4444]/10',
    warning: 'before:bg-[#F59E0B]/10',
    none: '',
  };

  return (
    <div className={cn(
      "relative overflow-hidden rounded-2xl bg-[#0B1020]/80 backdrop-blur-xl",
      "border border-white/[0.04] shadow-[0_8px_32px_0_rgba(0,0,0,0.36)]",
      "before:absolute before:inset-0 before:-z-10 before:blur-2xl before:transition-all",
      glowMap[glowColor],
      className
    )}>
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none" />
      {children}
    </div>
  );
}