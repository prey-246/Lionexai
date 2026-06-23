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
    primary: 'before:bg-[#0FA89A]/12',
    accent: 'before:bg-[#CFA43B]/12',
    danger: 'before:bg-[#FF4D67]/12',
    warning: 'before:bg-[#F5B23B]/12',
    none: '',
  };

  return (
    <div className={cn(
      "relative overflow-hidden rounded-2xl bg-[#101216]/85 backdrop-blur-xl",
      "border border-white/[0.06] shadow-[0_16px_44px_0_rgba(0,0,0,0.45)]",
      "before:absolute before:inset-0 before:-z-10 before:blur-2xl before:transition-all",
      glowMap[glowColor],
      className
    )}>
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.035] to-transparent pointer-events-none" />
      {children}
    </div>
  );
}