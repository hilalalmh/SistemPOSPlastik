export function BarChart({
  data,
  height = 200,
  valueFormatter = (value: number) => String(value),
}: {
  data: { label: string; value: number }[]
  height?: number
  valueFormatter?: (value: number) => string
}) {
  const max = data.reduce((acc, d) => (d.value > acc ? d.value : acc), 0)

  return (
    <div className="px-4 pb-4">
      <div className="flex items-end gap-1" style={{ height }}>
        {data.map((d) => {
          const pct = max > 0 ? (d.value / max) * 100 : 0
          return (
            <div
              key={d.label}
              className="group relative flex h-full flex-1 flex-col justify-end"
              title={`${d.label}: ${valueFormatter(d.value)}`}
            >
              <div
                className="w-full rounded-t bg-emerald-500/80 transition group-hover:bg-emerald-600"
                style={{ height: pct > 0 ? `${Math.max(pct, 2)}%` : '2px' }}
              />
            </div>
          )
        })}
      </div>
      <div className="mt-2 flex gap-1">
        {data.map((d) => (
          <div key={d.label} className="flex-1 truncate text-center text-[10px] text-slate-400">
            {d.label}
          </div>
        ))}
      </div>
    </div>
  )
}
