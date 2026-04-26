from services.llm_service import LLMService

class Router:
    ALL_CATEGORIES = ["بصل", "الشيكولاته", "زيوت نباتية"]  # exact folder names

    def __init__(self):
        self.llm = LLMService()

    def route(self, query: str):
        """Return a list of relevant categories (folder names) using LLM classification.
        The LLM receives a short prompt with the predefined list of possible categories and
        responds with a comma‑separated list of matches. If none match, an empty list is returned.
        """
        prompt = (
            "You are a classifier for food‑safety documents. Given the user query, "
            "list the relevant categories from the following list (comma‑separated). "
            "Reply ONLY with the category names. "
            "If none apply, return an empty string. Categories: "
            + ", ".join(self.ALL_CATEGORIES)
        )
        response = self.llm.classify_categories(prompt, self.ALL_CATEGORIES)
        # Parse response – assume comma‑separated, strip whitespace, filter unknowns
        categories = [c.strip() for c in response.split(",") if c.strip()]
        # Keep only categories that are in the allowed list
        categories = [c for c in categories if c in self.ALL_CATEGORIES]
        return categories