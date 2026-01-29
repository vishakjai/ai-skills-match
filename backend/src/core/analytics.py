from datetime import datetime
from typing import List, Dict, Set
from src.core.models import CandidateProfile, SkillProfileEntry, TimelineEntry
from src.core.graph import ontology

def parse_date(date_str: str) -> datetime:
    """
    Parses "YYYY-MM" or "Present" into a datetime object.
    Defaults to current time for "Present".
    """
    if not date_str:
        return datetime.now()
        
    if date_str.lower() == "present":
        return datetime.now()
        
    try:
        # standard YYYY-MM
        return datetime.strptime(date_str, "%Y-%m")
    except ValueError:
        try:
            # Fallback YYYY
            return datetime.strptime(date_str, "%Y")
        except:
            return datetime.now() # Fallback

def calculate_months(start: str, end: str) -> int:
    """
    Returns months between start and end.
    """
    s_date = parse_date(start)
    e_date = parse_date(end)
    
    # Calculate difference
    diff = (e_date.year - s_date.year) * 12 + (e_date.month - s_date.month)
    return max(1, diff) # Minimum 1 month

def calculate_analytics(profile: CandidateProfile) -> CandidateProfile:
    """
    Iterates through the timeline to calculate Deterministic YOE for every skill.
    Updates or creates entries in profile.skill_profile.
    """
    print("📊 Analytics: Calculating Deterministic Experience from Timeline...")
    
    # Track intervals per canonical skill to handle overlaps
    # Dict[canonical_slug, List[Tuple[date_start, date_end]]]
    skill_intervals_map: Dict[str, List[tuple]] = {}
    skill_duration_map: Dict[str, int] = {}
    
    # 1. Iterate Timeline and Collect Intervals
    if profile.timeline:
        for job in profile.timeline:
            s_date = parse_date(job.start_date)
            e_date = parse_date(job.end_date)
            
            # Ensure start <= end
            if s_date > e_date:
                s_date, e_date = e_date, s_date
                
            if job.extracted_skills:
                for skill_obj in job.extracted_skills:
                    canonical = ontology.resolve_alias(skill_obj.skill_id)
                    
                    if canonical not in skill_intervals_map:
                        skill_intervals_map[canonical] = []
                    
                    skill_intervals_map[canonical].append((s_date, e_date))

    # 2. Merge Intervals and Calculate Total Months per Skill
    for canonical, intervals in skill_intervals_map.items():
        if not intervals:
            continue
            
        # Sort by start date
        intervals.sort(key=lambda x: x[0])
        
        merged = []
        if intervals:
            curr_start, curr_end = intervals[0]
            for i in range(1, len(intervals)):
                next_start, next_end = intervals[i]
                
                if next_start <= curr_end: # Overlap
                    curr_end = max(curr_end, next_end)
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
            
        # Sum duration of merged intervals
        total_months = 0
        for start, end in merged:
            # (year_diff * 12) + month_diff
            diff = (end.year - start.year) * 12 + (end.month - start.month)
            total_months += max(1, diff) # Ensure at least 1 month
            
        skill_duration_map[canonical] = total_months
    
    # 2. Update Skill Profile
    # We want to preserve existing metadata (like "competency_level") if it exists,
    # but update the 'total_months'.
    
    # Index existing profile
    existing_profile_map = {ontology.resolve_alias(sp.skill_slug): sp for sp in profile.skill_profile}
    
    new_profile_list = []
    
    # A. Update existing entries
    for canonical, total_months in skill_duration_map.items():
        if canonical in existing_profile_map:
            # Update existing
            entry = existing_profile_map[canonical]
            # Take the MAX of AI guess vs Calculated? Or just Sum?
            # User wants "Time Spent". Calculation is truth.
            # But overlapping jobs? (e.g. 2 jobs at same time).
            # Simple sum might double count.
            # Ideally we process distinct time periods. 
            # For V1, Simple Sum is acceptable proxy for "Intensity".
            # Or we can just trust the calculation.
            entry.total_months = total_months 
            new_profile_list.append(entry)
        else:
            # New entry found in timeline but not in header
            new_entry = SkillProfileEntry(
                skill_slug=canonical,
                total_months=total_months,
                competency_level="unknown", # Will be inferred by Engine later
                sources=["experience"]
            )
            new_profile_list.append(new_entry)
            
    # B. Keep entries that were in Profile but NOT in Timeline (e.g. "Git" in header but not in descriptions)
    processed_slugs = set(skill_duration_map.keys())
    for sp in profile.skill_profile:
        canonical = ontology.resolve_alias(sp.skill_slug)
        if canonical not in processed_slugs:
            new_profile_list.append(sp)
            
    profile.skill_profile = new_profile_list
    
    print(f"📊 Analytics: Enhanced {len(new_profile_list)} skills with timeline data.")
    return profile
