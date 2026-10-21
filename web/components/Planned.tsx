export default function Planned({ title, what }: { title: string; what: string }) {
  return (
    <section>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-slate-600">{what}</p>
      <p className="mt-1 text-sm text-slate-500">Not built yet.</p>
    </section>
  );
}
