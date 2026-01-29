import React from 'react';

interface JDSkillRowProps {
    id: string; // req_id
    skillName: string;
    level: "junior" | "mid" | "senior";
    isHardFilter: boolean;
    priority: "must_have" | "nice_to_have";
    onChange: (id: string, updates: { level?: "junior" | "mid" | "senior"; isHardFilter?: boolean }) => void;
    onDelete?: (id: string) => void;
}

export const JDSkillRow: React.FC<JDSkillRowProps> = ({ id, skillName, level, isHardFilter, priority, onChange, onDelete }) => {
    const levelVal = level === "junior" ? 1 : level === "mid" ? 2 : 3;

    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = parseInt(e.target.value);
        const newLevel = val === 1 ? "junior" : val === 2 ? "mid" : "senior";
        onChange(id, { level: newLevel });
    };

    const isMustHave = priority === "must_have";

    return (
        <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200 mb-2 hover:bg-slate-50 transition-colors">
            <div className="flex items-center gap-3 w-1/3">
                <span className={`px-2 py-1 text-xs font-semibold rounded ${isMustHave ? 'bg-indigo-100 text-indigo-700' : 'bg-green-100 text-green-700'}`}>
                    {isMustHave ? "Required" : "Preferred"}
                </span>
                <span className="font-medium text-slate-800 truncate" title={skillName}>
                    {skillName}
                </span>
                {onDelete && (
                    <button
                        onClick={() => onDelete(id)}
                        className="p-1 text-slate-400 hover:text-rose-500 rounded-full hover:bg-rose-50 transition-colors"
                        title="Remove Skill"
                    >
                        ✕
                    </button>
                )}
            </div>

            <div className="flex items-center gap-6 w-2/3 justify-end">
                {/* Expertise Slider */}
                <div className="flex items-center gap-3 w-48">
                    <span className="text-xs text-slate-500 w-12 text-right font-medium uppercase">
                        {level}
                    </span>
                    <input
                        type="range"
                        min="1"
                        max="3"
                        step="1"
                        value={levelVal}
                        onChange={handleSliderChange}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                    />
                </div>

                {/* Hard Filter Checkbox - Only for Must Have */}
                <div className="w-32 flex justify-end">
                    {isMustHave ? (
                        <label className="flex items-center cursor-pointer gap-2">
                            <input
                                type="checkbox"
                                checked={isHardFilter}
                                onChange={(e) => onChange(id, { isHardFilter: e.target.checked })}
                                className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
                            />
                            <span className={`text-sm ${isHardFilter ? 'font-semibold text-rose-600' : 'text-slate-500'}`}>
                                {isHardFilter ? "Critical" : "Flexible"}
                            </span>
                        </label>
                    ) : (
                        <span className="text-xs text-slate-400 italic">Nice to have</span>
                    )}
                </div>
            </div>
        </div>
    );
};
