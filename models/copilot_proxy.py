"""
GitHub Copilot Proxy for CodePolice
Provides AI-powered code fix suggestions using GitHub Copilot API
"""

import os
import time
import hashlib
import json
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass

# Optional dependencies
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CopilotProxy")


@dataclass
class CopilotConfig:
    """Configuration for Copilot integration"""
    api_endpoint: str = "https://api.github.com/copilot_internal "
    auth_token: str = os.getenv("COPILOT_TOKEN")
    cache_dir: Path = Path(".copilot_cache")
    rate_limit: int = 10  # Requests per minute
    timeout: int = 10  # Seconds
    enabled: bool = True


class CopilotRateLimiter:
    """Simple rate limiter for API requests"""

    def __init__(self, max_calls: int, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def allow_request(self) -> bool:
        """Check if request is allowed based on rate limit"""
        now = time.time()
        # Remove old calls
        self.calls = [t for t in self.calls if t > now - self.period]

        if len(self.calls) >= self.max_calls:
            return False

        self.calls.append(now)
        return True


class CopilotFixer:
    """
    GitHub Copilot API Proxy for code fix suggestions
    Falls back to rule-based fixes when unavailable
    """

    def __init__(self, config: Optional[CopilotConfig] = None):
        self.config = config or CopilotConfig()
        self.cache = {}
        self.rate_limiter = CopilotRateLimiter(self.config.rate_limit)
        self._init_cache()

    def _init_cache(self) -> None:
        """Initialize cache directory"""
        if not self.config.cache_dir.exists():
            self.config.cache_dir.mkdir(parents=True)

    def _get_cache_key(self, code_snippet: str) -> str:
        """Generate cache key for code snippet"""
        return hashlib.sha256(code_snippet.encode()).hexdigest()

    def _load_from_cache(self, key: str) -> Optional[str]:
        """Load cached response if exists and valid"""
        cache_file = self.config.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)

            # Check expiration (24 hours)
            if time.time() - data.get("timestamp", 0) < 86400:
                return data.get("response")
        except Exception as e:
            logger.warning(f"Cache load error: {e}")
            return None

    def _save_to_cache(self, key: str, response: str) -> None:
        """Save response to cache"""
        cache_file = self.config.cache_dir / f"{key}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    "timestamp": time.time(),
                    "response": response
                }, f)
        except Exception as e:
            logger.warning(f"Cache save error: {e}")

    def get_suggestion(
            self,
            code_snippet: str,
            context: Optional[Dict] = None
    ) -> str:
        """
        Get AI-powered code suggestion from GitHub Copilot
        Returns fallback suggestion if Copilot is unavailable
        """
        if not self.config.enabled:
            return self._fallback_suggestion(code_snippet)

        if not REQUESTS_AVAILABLE:
            logger.warning("Requests library not available - using fallback suggestions")
            return self._fallback_suggestion(code_snippet)

        if not self.config.auth_token:
            logger.warning("GitHub Copilot token not configured - using fallback suggestions")
            return self._fallback_suggestion(code_snippet)

        cache_key = self._get_cache_key(code_snippet)
        cached = self._load_from_cache(cache_key)

        if cached:
            return cached

        if not self.rate_limiter.allow_request():
            logger.warning("GitHub Copilot rate limit exceeded - using fallback suggestions")
            return self._fallback_suggestion(code_snippet)

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.config.auth_token}",
            "Content-Type": "application/json",
            "User-Agent": "CodePolice/1.0"
        }

        prompt = self._build_prompt(code_snippet, context)

        try:
            response = requests.post(
                self.config.api_endpoint,
                headers=headers,
                json={"prompt": prompt},
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                suggestion = response.json().get("choices", [{}])[0].get("text", "")
                self._save_to_cache(cache_key, suggestion)
                return suggestion
            else:
                logger.warning(f"Copilot API error: {response.status_code} - {response.text}")
                return self._fallback_suggestion(code_snippet)

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return self._fallback_suggestion(code_snippet)

    def _build_prompt(self, code_snippet: str, context: Optional[Dict] = None) -> str:
        """Build prompt for Copilot based on code and context"""
        prompt = f"Please fix this Python code:\n{code_snippet}\n\n"

        if context:
            prompt += "Context:\n"
            for key, value in context.items():
                prompt += f"{key}: {value}\n"

        prompt += "\nFixed version:\n"
        return prompt

    def _fallback_suggestion(self, code_snippet: str) -> str:
        """
        Fallback rule-based suggestion when Copilot is unavailable
        Implements basic code cleanup strategies
        """
        # Example fallback logic - should be replaced with actual rules
        lines = code_snippet.strip().split('\n')

        if "password = " in lines[0] and "'" in lines[0]:
            return "import os\npassword = os.getenv('DB_PASSWORD')"

        if "eval(" in lines[0]:
            return "import ast\nresult = ast.literal_eval(input_str)"

        # Default fallback
        return "# Consider refactoring this code for better security and performance"


# Configuration management
def load_copilot_config() -> CopilotConfig:
    """Load configuration from environment variables or config file"""
    return CopilotConfig(
        auth_token=os.getenv("COPILOT_TOKEN"),
        enabled=os.getenv("COPILOT_ENABLED", "true").lower() == "true"
    )


# Example usage with code police core
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Copilot Fixer CLI")
    parser.add_argument("--code", required=True, help="Code snippet to fix")
    parser.add_argument("--context", type=json.loads, help="JSON context for the code")

    args = parser.parse_args()

    copilot = CopilotFixer()
    suggestion = copilot.get_suggestion(args.code, args.context)

    print("AI Suggestion:")
    print(suggestion)