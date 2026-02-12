import React, { useState } from 'react';
import type { JobDescription } from './api';
import { JDSkillRow } from './JDSkillRow';
import { Bot, MapPin, GraduationCap, ArrowRight, Plus } from 'lucide-react';

interface JDConfigurationViewProps {
    jd: JobDescription;
    onConfirm: (updatedJD: JobDescription) => void;
    onCancel: () => void;
}

export const JDConfigurationView: React.FC<JDConfigurationViewProps> = ({ jd, onConfirm, onCancel }) => {
    const [localJD, setLocalJD] = useState<JobDescription>(JSON.parse(JSON.stringify(jd)));

    // Toggle Global Filter
    const toggleStrictGating = (field: 'education_strict' | 'location_strict') => {
        setLocalJD(prev => ({
            ...prev,
            gating_rules: {
                ...prev.gating_rules,
                [field]: !prev.gating_rules[field]
            }
        }));
    };

    // Handle Requirement Change
    const handleReqChange = (id: string, updates: { level?: "junior" | "mid" | "senior"; isHardFilter?: boolean }) => {
        setLocalJD(prev => ({
            ...prev,
            requirements: prev.requirements.map(req => {
                if (req.req_id !== id) return req;
                const mapped: Partial<typeof req> = {};
                if (updates.level !== undefined) mapped.level = updates.level;
                if (updates.isHardFilter !== undefined) mapped.is_hard_filter = updates.isHardFilter;
                return { ...req, ...mapped };
            })
        }));
    };

    const [newSkillName, setNewSkillName] = useState("");
    const [isAdding, setIsAdding] = useState(false);

    const mustHave = localJD.requirements.filter(r => r.priority === 'must_have');
    const niceToHave = localJD.requirements.filter(r => r.priority === 'nice_to_have');

    // Add Skill Handler
    const handleAddSkill = () => {
        if (!newSkillName.trim()) return;

        const newReq = {
            req_id: `manual_${Date.now()}`,
            skill_id: newSkillName.trim(), // In a real app we'd map this to ID
            priority: 'must_have' as const,
            level: 'mid' as const,
            is_hard_filter: false,
            min_years: 0
        };

        setLocalJD(prev => ({
            ...prev,
            requirements: [newReq, ...prev.requirements]
        }));

        setNewSkillName("");
        setIsAdding(false);
    };

    // Delete Skill Handler
    const handleDeleteSkill = (id: string) => {
        setLocalJD(prev => ({
            ...prev,
            requirements: prev.requirements.filter(r => r.req_id !== id)
        }));
    };

    return (
        <div className="max-w-4xl mx-auto p-6 bg-white rounded-xl shadow-sm border border-slate-200 mt-6">
            <div className="flex items-center gap-3 mb-6 border-b pb-4">
                <div className="p-2 bg-indigo-100 rounded-lg text-indigo-600">
                    <Bot size={24} />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-slate-800">
                        {localJD.job_metadata.title || "Job Configuration"}
                    </h2>
                    <p className="text-sm text-slate-500">Refine requirements relative to your hiring bar.</p>
                </div>
            </div>

            {/* Global Filters */}
            <div className="grid grid-cols-2 gap-4 mb-8">
                <div className={`p-4 rounded-lg border cursor-pointer border-slate-200 hover:border-indigo-300 transition-colors bg-slate-50 relative`}>
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2 text-slate-700 font-semibold mb-1">
                            <GraduationCap size={18} />
                            <span>Education Filter</span>
                        </div>
                        <input
                            type="checkbox"
                            checked={localJD.gating_rules.education_strict || false}
                            onChange={() => toggleStrictGating('education_strict')}
                            className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                    </div>
                    <p className="text-sm text-slate-500">
                        Required: <span className="font-medium text-slate-700">{localJD.gating_rules.education_min || "None"}</span>
                    </p>
                    {localJD.gating_rules.education_strict && <span className="absolute bottom-2 right-4 text-xs font-bold text-rose-600">STRICT MODE</span>}
                </div>

                <div className={`p-4 rounded-lg border cursor-pointer border-slate-200 hover:border-indigo-300 transition-colors bg-slate-50 relative`}>
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2 text-slate-700 font-semibold mb-1">
                            <MapPin size={18} />
                            <span>Location Filter</span>
                        </div>
                        <input
                            type="checkbox"
                            checked={localJD.gating_rules.location_strict || false}
                            onChange={() => toggleStrictGating('location_strict')}
                            className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                        />
                    </div>
                    <p className="text-sm text-slate-500">
                        Based in: <span className="font-medium text-slate-700">{localJD.job_metadata.location || "Any"}</span>
                    </p>
                    {localJD.gating_rules.location_strict && <span className="absolute bottom-2 right-4 text-xs font-bold text-rose-600">STRICT MODE</span>}
                </div>
            </div>

            {/* Skills Configuration */}
            <div className="mb-8">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Required Skills ({mustHave.length})</h3>
                    <button
                        onClick={() => setIsAdding(!isAdding)}
                        className="text-xs flex items-center gap-1 text-indigo-600 font-bold hover:bg-indigo-50 px-2 py-1 rounded transition-colors"
                    >
                        <Plus size={14} /> Add Skill
                    </button>
                </div>

                {/* Add Skill Input */}
                {isAdding && (
                    <div className="flex gap-2 mb-4 animate-fade-in">
                        <input
                            type="text"
                            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                            placeholder="Enter skill name (e.g. Docker)..."
                            value={newSkillName}
                            onChange={(e) => setNewSkillName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
                            autoFocus
                        />
                        <button
                            onClick={handleAddSkill}
                            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-bold hover:bg-indigo-700 disabled:opacity-50"
                            disabled={!newSkillName.trim()}
                        >
                            Add
                        </button>
                    </div>
                )}

                {mustHave.map(req => (
                    <JDSkillRow
                        key={req.req_id}
                        id={req.req_id}
                        skillName={req.skill_id || req.req_id}
                        level={req.level || 'mid'}
                        isHardFilter={req.is_hard_filter ?? false}
                        priority={req.priority}
                        onChange={handleReqChange}
                        onDelete={handleDeleteSkill}
                    />
                ))}

                {niceToHave.length > 0 && (
                    <>
                        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mt-6 mb-4">Preferred Skills ({niceToHave.length})</h3>
                        {niceToHave.map(req => (
                            <JDSkillRow
                                key={req.req_id}
                                id={req.req_id}
                                skillName={req.skill_id || req.req_id}
                                level={req.level || 'mid'}
                                isHardFilter={false} // Preferred are never hard filters
                                priority={req.priority}
                                onChange={handleReqChange}
                                onDelete={handleDeleteSkill}
                            />
                        ))}
                    </>
                )}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t sticky bottom-0 bg-white pb-2">
                <button
                    onClick={onCancel}
                    className="px-4 py-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors font-medium"
                >
                    Cancel
                </button>
                <button
                    onClick={() => onConfirm(localJD)}
                    className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm font-medium flex items-center gap-2 transition-all hover:scale-105"
                >
                    Proceed to Matching <ArrowRight size={18} />
                </button>
            </div>
        </div>
    );
};
