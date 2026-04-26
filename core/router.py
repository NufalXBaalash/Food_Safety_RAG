from services.llm_service import LLMService
from config.settings import settings
from utils.logger import logger

class Router:
    @property
    def ALL_CATEGORIES(self):
        return list(settings.active_cluster_map.keys())

    def __init__(self):
        self.llm = LLMService()

    def route(self, query: str):
        """Return a list of relevant categories (folder names) using LLM classification.
        The LLM receives a prompt with the predefined list of possible categories and
        responds with matches.
        """
        # Build a mapping of normalized names to actual names for better matching
        # (Handles common Arabic spelling variations internally if needed)
        # Fast Path: Check if query has high overlap with any category directly
        query_words = set(query.lower().split())
        for official in self.ALL_CATEGORIES:
            official_words = set(official.lower().split())
            if len(query_words.intersection(official_words)) >= max(1, len(official_words) * 0.7):
                logger.info(f"Fast Router Match: {official}")
                return [official]

        prompt = (
            "You are an expert classifier for food‑safety regulatory documents.\n"
            f"User Query: \"{query}\"\n\n"
            "Identify which of the following categories are relevant to the query. "
            "Reply with a comma‑separated list of the EXACT category names from the list below. "
            "If multiple categories apply, list them all. If none apply, return an empty string.\n\n"
            "ALLOWED CATEGORIES:\n"
            + "\n".join([f"- {c}" for c in self.ALL_CATEGORIES])
            + "\n\nResponse format: Category1, Category2, ..."
        )
        
        response = self.llm.classify_categories(prompt, self.ALL_CATEGORIES)
        logger.info(f"Router LLM raw response: '{response}'")
        
        if not response:
            return []

        # Parse response – handle markdown, quotes, and various separators
        import re
        # Remove markdown code blocks
        clean_text = re.sub(r'```.*?```', '', response, flags=re.DOTALL).strip()
        if not clean_text: # If everything was in code blocks
            clean_text = response.replace('```', '').strip()
            
        # Split by comma or newline
        candidates = re.split(r'[,\n]', clean_text)
        
        categories = []
        for cand in candidates:
            # Strip common decorators
            name = cand.strip().strip('"').strip("'").strip('*').strip('-').strip()
            if not name: continue
            
            if name in self.ALL_CATEGORIES:
                categories.append(name)
            else:
                # Fuzzy match using normalization
                norm_name = settings.normalize_arabic(name)
                for official in self.ALL_CATEGORIES:
                    if norm_name == settings.normalize_arabic(official) or name.lower() == official.lower():
                        categories.append(official)
                        break
        
        # Map back to English names for Pinecone filtering
        cluster_map = settings.active_cluster_map
        selected_english = []
        for cat in categories:
            eng = cluster_map.get(cat)
            if eng:
                selected_english.append(eng)
            else:
                # Fallback: check if cat is already an English name or needs fuzzy mapping
                # (Though usually it should be in the map)
                selected_english.append(cat)
        
        # Deduplicate
        selected_english = list(dict.fromkeys(selected_english))
        logger.info(f"Router selected (mapped to English): {selected_english}")
        return selected_english