import re
from typing import List, Optional, Dict

class MetadataExtractor:
    def __init__(self):
        self.locations = [
            "Remote", "Hybrid", "Onsite",
            "New York", "San Francisco", "London", "Berlin", "Bangalore", "Singapore",
            "Austin", "Seattle", "Boston"
        ]
        
        self.domains = [
            "Fintech", "HealthTech", "AdTech", "EdTech", "E-commerce",
            "SaaS", "Cybersecurity", "Blockchain", "AI/ML", "Gaming"
        ]

    def extract_experience(self, text: str) -> int:
        """
        Extracts minimum years of experience using stronger context patterns.
        """
        # Patterns with explicit "experience" context
        patterns = [
            r'min(?:imum)?\s*(\d+)\+?\s*years?',   # "Minimum 5 years"
            r'at\s*least\s*(\d+)\+?\s*years?',     # "At least 3 years"
            r'(\d+)\+?\s*years?\s*(?:of)?\s*experience', # "5+ years experience"
        ]
        
        for p in patterns:
            matches = re.findall(p, text.lower())
            if matches:
                 # Take the max found in these explicit patterns
                 # (e.g. "5+ years experience... prefer 7+ years" -> 7 might be better? 
                 # Or usually min is what we want? Let's take the first one explicitly found as 'min' or 'at least' if present, else max)
                 
                 vals = [int(m) for m in matches if m.isdigit()]
                 if vals:
                     return max(vals) * 12

        # Fallback to looser pattern if explicit context missing
        # But be careful not to pick up dates like "2020"
        loose_matches = re.findall(r'(\d+)\+?\s*years?', text.lower())
        valid_years = []
        for m in loose_matches:
            try:
                val = int(m)
                if 1 <= val <= 15: # Reasonable range for years of experience
                    valid_years.append(val)
            except: pass
            
        if valid_years:
            return max(valid_years) * 12
            
        return 0

    def extract_location(self, text: str) -> Optional[str]:
        """
        Finds location using "Location:" prefix + Keywords.
        """
        # 1. Prefix Search (High Confidence)
        # Look for "Location: New York" or "Based in: Remote"
        prefix_pattern = r'(?:location|based in|office):\s*([a-zA-Z\s,/]+)'
        matches = re.findall(prefix_pattern, text.lower())
        
        for m in matches:
            snippet = m.strip()
            # Check if this snippet contains any of our known locations
            for loc in self.locations:
                if loc.lower() in snippet:
                    return loc # High confidence return
        
        # 2. Fallback: Keyword Search (Lower Confidence)
        # But strictly look for "Remote" or "Hybrid" as they are usually distinct
        text_title = text.title()
        
        if "Remote" in text_title: return "Remote"
        if "Hybrid" in text_title: return "Hybrid"
        
        # 3. Last Resort: City Names
        found = []
        for loc in self.locations:
            if loc in text_title:
                found.append(loc)
        
        if found: return found[0]
        return None

    def extract_domains(self, text: str) -> List[str]:
        """
        Finds domain keywords.
        """
        text_title = text.title()
        found = set()
        for dom in self.domains:
            if dom in text_title or dom.upper() in text.upper():
                found.add(dom)
        return list(found)

    # ... (Keep existing methods, extend logic)

    def extract_visa(self, text: str) -> bool:
        """
        Returns True if sponsorship is likely available, False if explicitly restricted, None if neutral.
        Heuristics:
        - "US Citizen only" -> False (Sponsorship=False)
        - "Green Card" -> False
        - "Visa sponsorship available" -> True
        """
        text_lower = text.lower()
        if "citizen only" in text_lower or "u.s. citizen" in text_lower or "no sponsorship" in text_lower:
            return False
        if "sponsorship available" in text_lower or "will sponsor" in text_lower:
            return True
        return None # Unknown

    def extract_education(self, text: str) -> Optional[str]:
        """
        Finds minimum education.
        """
        text_lower = text.lower()
        if "phd" in text_lower or "doctorate" in text_lower:
            return "PhD"
        if "master" in text_lower or "ms " in text_lower or "m.s." in text_lower:
            return "Masters"
        if "bachelor" in text_lower or "bs " in text_lower or "b.s." in text_lower:
            return "Bachelors"
        return None

    def extract_clearance(self, text: str) -> str:
        text_upper = text.upper()
        if "TS/SCI" in text_upper: return "TS/SCI"
        if "TOP SECRET" in text_upper: return "Top Secret"
        if "SECRET" in text_upper: return "Secret"
        if "PUBLIC TRUST" in text_upper: return "Public Trust"
        return "None"

    def extract_seniority(self, text: str) -> Dict:
        text_lower = text.lower()
        levels = []
        if "principal" in text_lower: levels.append("Principal")
        if "staff" in text_lower: levels.append("Staff")
        if "senior" in text_lower: levels.append("Senior")
        if "lead" in text_lower: levels.append("Lead")
        if "junior" in text_lower or "associate" in text_lower: levels.append("Junior")
        
        target = levels[0] if levels else "Mid-Level" # Heuristic: pick highest or first found
        return {
            "target_level": target,
            "keywords_found": levels
        }

    def extract_advanced(self, text: str) -> Dict:
        base = self.extract_all(text) # Gets location, domain, exp
        return {
            **base,
            "visa_sponsorship": self.extract_visa(text),
            "education_min": self.extract_education(text),
            "clearance": self.extract_clearance(text),
            "seniority": self.extract_seniority(text)
        }
