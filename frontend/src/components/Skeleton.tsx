export function SkeletonCards({ count = 5 }: { count?: number }) {
  return (
    <div className="cards">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card" style={{ cursor: "default" }}>
          <div className="skeleton" style={{ height: 16, width: "60%", marginBottom: 10 }} />
          <div className="skeleton" style={{ height: 12, width: "80%", marginBottom: 6 }} />
          <div className="skeleton" style={{ height: 12, width: "40%", marginBottom: 16 }} />
          <div className="skeleton" style={{ height: 28, width: "30%" }} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonPanels({ count = 3 }: { count?: number }) {
  return (
    <div className="flex-col">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 160 }} />
      ))}
    </div>
  );
}
