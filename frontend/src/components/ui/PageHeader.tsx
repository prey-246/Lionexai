export function PageHeader({ title, subtitle }: { title: string, subtitle: string }) {
  return (
    <div>
      <h1 className="text-3xl font-serif font-bold text-text-primary">{title}</h1>
      <p className="mt-1 text-sm text-text-muted">{subtitle}</p>
    </div>
  );
}