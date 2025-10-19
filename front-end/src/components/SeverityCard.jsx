import React from "react";

const LABEL_COLORS = {
  mild: "bg-green-500",
  moderate: "bg-amber-500",
  severe: "bg-red-600",
};

const nice = (x) => (x == null || isNaN(x) ? "—" : `${(x * 100).toFixed(0)}%`);

export default function SeverityCard({ severity }) {
  if (!severity) return null;
  const { label, probabilities } = severity;
  return (
    <div className="rounded-2xl shadow-md p-4 border border-zinc-800 bg-zinc-900/50">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold">Severity assessment</h3>
        <span
          className={`px-3 py-1 text-sm rounded-full text-white ${LABEL_COLORS[label] || "bg-zinc-600"}`}
        >
          {label?.toUpperCase() || "UNKNOWN"}
        </span>
      </div>

      <div className="space-y-2">
        {["mild", "moderate", "severe"].map((k) => (
          <div key={k}>
            <div className="flex justify-between text-sm">
              <span className="capitalize">{k}</span>
              <span className="tabular-nums">{nice(probabilities?.[k])}</span>
            </div>
            <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden">
              <div
                className={`${LABEL_COLORS[k] || "bg-zinc-600"} h-2`}
                style={{
                  width: `${Math.max(0, Math.min(100, Math.round((probabilities?.[k] || 0) * 100)))}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-zinc-400 mt-3">
        Severity is estimated from your symptoms and details (age, duration,
        vitals). This is not a diagnosis.
      </p>
    </div>
  );
}
