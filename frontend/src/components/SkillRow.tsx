import type { TraceItem } from '../api';

export const SkillRow = ({ item }: { item: TraceItem }) => (
    <div className={"flex flex-col p-3 rounded-lg border transition-all hover:scale-[1.01] " +
        (item.status === 'matched' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' :
            item.status === 'partial' ? 'bg-amber-500/10 border-amber-500/20 text-amber-300' :
                'bg-red-500/10 border-red-500/20 text-red-300')}>

        <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
                <span className={"flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold " +
                    (item.status === 'matched' ? 'bg-emerald-500 text-black' :
                        item.status === 'partial' ? 'bg-amber-500 text-black' :
                            'bg-red-500 text-black')}>
                    {item.status === 'matched' ? '✓' : item.status === 'partial' ? '~' : '✕'}
                </span>
                <span className="font-bold capitalize">{item.skill_slug.replace(/_/g, " ")}</span>
            </div>

            <div className="flex items-center gap-2">
                {item.seniority_level !== 'unknown' && (
                    <span className="text-[10px] uppercase px-2 py-0.5 rounded border border-current opacity-60">
                        {item.seniority_level}
                    </span>
                )}
                {/* Score Badge */}
                <span className="text-[10px] font-mono opacity-50" title="Match Confidence Score">
                    Match: {(item.score * 100).toFixed(0)}%
                </span>
            </div>
        </div>

        {item.sources && item.sources.length > 0 && (
            <div className="mt-2 text-[10px] opacity-60 ml-9 flex gap-2">
                {item.sources.map(s => (
                    <span key={s} className="px-1.5 py-0.5 bg-black/20 rounded uppercase tracking-wider">{s}</span>
                ))}
            </div>
        )}
    </div>
);
