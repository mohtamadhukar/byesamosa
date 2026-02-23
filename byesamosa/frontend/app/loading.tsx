export default function Loading() {
  return (
    <main className="min-h-screen max-w-6xl mx-auto px-6 py-10">
      <div className="animate-pulse space-y-8">
        <div>
          <div className="h-12 w-64 bg-warm-200 rounded-lg" />
          <div className="h-5 w-40 bg-warm-200 rounded mt-2" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-80 bg-white rounded-xl shadow-sm" />
          ))}
        </div>
        <div className="h-64 bg-white rounded-xl shadow-sm" />
        <div className="h-48 bg-white rounded-xl shadow-sm" />
      </div>
    </main>
  );
}
