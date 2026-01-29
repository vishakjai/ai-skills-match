import type { AnalysisSection } from '../api';

export const AnalysisCard = ({ section }: { section?: AnalysisSection }) => {
    if (!section) return null;

    const statusColors = {
        met: "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
        not_met: "bg-red-500/10 border-red-500/20 text-red-300",
        review_needed: "bg-amber-500/10 border-amber-500/20 text-amber-300",
        exceeds: "bg-purple-500/10 border-purple-500/20 text-purple-300",
    };

    const statusIcons = {
        met: "✅",
        not_met: "❌",
        review_needed: "⚠️",
        exceeds: "🚀",
    };

    return (
        <div className={"p-4 rounded-xl border mb-4 backdrop-blur-sm " + statusColors[section.status]}>
            <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-lg flex items-center gap-2">
                    <span>{statusIcons[section.status]}</span>
                    {section.title} Analysis
                </h3>
                <span className="text-xs font-mono uppercase opacity-70 px-2 py-1 bg-black/20 rounded">
                    {section.status.replace("_", " ")}
                </span>
            </div>
            <p className="text-sm font-medium mb-3">{section.summary}</p>
            {section.details.length > 0 && (
                <ul className="space-y-1">
                    {section.details.map((detail, idx) => (
                        <li key={idx} className="text-xs opacity-80 pl-4 border-l-2 border-current/30">
                            {detail}
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};
