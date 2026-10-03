"""
MockLLMClient — deterministic LLM mock for offline demo and testing.
Returns realistic WorkflowSpec fixtures based on prompt keywords.
"""
from __future__ import annotations

import hashlib
from pydantic import BaseModel


# ── Preset WorkflowSpec fixtures ──────────────────────────────────────────────

def _startup_spec() -> dict:
    return {
        "title": "Seed-Stage AI Startups in India",
        "intent_summary": "Collect detailed profiles of early-stage AI companies founded in India, including funding, founders, and career information.",
        "entity_type": "startup",
        "fields": [
            {"name": "name", "label": "Company Name", "type": "string", "description": "Legal name of the startup", "required": True, "unique_key": True, "validators": ["min_len:2"]},
            {"name": "founders", "label": "Founders", "type": "string", "description": "Comma-separated list of founder names", "required": True, "unique_key": False, "validators": []},
            {"name": "funding_amount", "label": "Funding Amount", "type": "currency", "description": "Total funding raised with round type (e.g. $41M Series A)", "required": False, "unique_key": False, "validators": []},
            {"name": "location", "label": "Location", "type": "string", "description": "City and country of headquarters", "required": False, "unique_key": False, "validators": []},
            {"name": "career_page_url", "label": "Careers Page", "type": "url", "description": "Direct link to the company's careers or jobs page", "required": False, "unique_key": False, "validators": ["url"]},
            {"name": "description", "label": "Description", "type": "string", "description": "One-sentence description of the company's core product or service", "required": False, "unique_key": False, "validators": ["min_len:10"]},
            {"name": "stage", "label": "Stage", "type": "enum", "description": "Funding stage: Pre-Seed, Seed, Series A, Series B, etc.", "required": False, "unique_key": False, "enum_values": ["Pre-Seed", "Seed", "Series A", "Series B", "Series C", "Growth"], "validators": []},
        ],
        "source_strategy": {
            "connectors": ["web_search", "rss", "hackernews"],
            "seed_queries": [
                "seed stage AI startup India 2024 funding",
                "India AI company founded funding crunchbase",
                "YourStory Indian AI startup funding round",
                "Inc42 AI startup India series A seed",
            ],
            "seed_urls": [],
            "domain_allowlist": [],
            "domain_blocklist": ["linkedin.com", "facebook.com"],
            "rationale": "Web search covers news articles; RSS feeds from YourStory/Inc42 provide structured startup news; HN surfaces emerging companies mentioned by the tech community.",
        },
        "dag": [
            {"id": "n1", "type": "discover_sources", "depends_on": [], "params": {}, "label": "Discover Sources"},
            {"id": "n2", "type": "fetch", "depends_on": ["n1"], "params": {}, "label": "Fetch Pages"},
            {"id": "n3", "type": "extract", "depends_on": ["n2"], "params": {}, "label": "Extract Entities"},
            {"id": "n4", "type": "normalize", "depends_on": ["n3"], "params": {}, "label": "Normalize Fields"},
            {"id": "n5", "type": "validate", "depends_on": ["n4"], "params": {}, "label": "Validate Data"},
            {"id": "n6", "type": "dedupe", "depends_on": ["n5"], "params": {}, "label": "Deduplicate"},
            {"id": "n7", "type": "score", "depends_on": ["n6"], "params": {}, "label": "Score Confidence"},
            {"id": "n8", "type": "finalize", "depends_on": ["n7"], "params": {}, "label": "Finalize"},
        ],
        "limits": {"max_pages": 30, "max_records": 50, "per_domain_rps": 1.0},
        "assumptions": [
            "Focusing on companies with at least some public funding information.",
            "Targeting companies founded after 2018.",
        ],
        "clarifying_questions": ["Should I include AI-adjacent companies (e.g. SaaS with AI features) or only pure AI companies?"],
        "risk_notes": ["LinkedIn company pages are login-walled and excluded.", "Crunchbase requires login for detailed data; using public search results only."],
    }


def _jobs_spec() -> dict:
    return {
        "title": "Remote Python Internship Opportunities",
        "intent_summary": "Collect current remote internship postings for Python developers from permitted job boards and tech company sites.",
        "entity_type": "job_opening",
        "fields": [
            {"name": "title", "label": "Job Title", "type": "string", "description": "Exact job title as posted", "required": True, "unique_key": True, "validators": ["min_len:3"]},
            {"name": "company", "label": "Company", "type": "string", "description": "Name of the hiring company", "required": True, "unique_key": False, "validators": []},
            {"name": "location", "label": "Location", "type": "string", "description": "Location or 'Remote' if fully remote", "required": False, "unique_key": False, "validators": []},
            {"name": "requirements", "label": "Requirements", "type": "string", "description": "Key technical skills required", "required": False, "unique_key": False, "validators": []},
            {"name": "stipend", "label": "Stipend", "type": "currency", "description": "Monthly or total stipend amount if mentioned", "required": False, "unique_key": False, "validators": []},
            {"name": "apply_url", "label": "Apply URL", "type": "url", "description": "Direct link to the application form", "required": True, "unique_key": False, "validators": ["url"]},
            {"name": "deadline", "label": "Application Deadline", "type": "date", "description": "Last date to apply if mentioned", "required": False, "unique_key": False, "validators": []},
        ],
        "source_strategy": {
            "connectors": ["web_search", "rss"],
            "seed_queries": [
                "remote Python internship 2024 apply",
                "Python developer intern remote stipend",
                "software engineering internship Python remote 2024",
            ],
            "seed_urls": [],
            "domain_allowlist": [],
            "domain_blocklist": ["linkedin.com", "indeed.com"],
            "rationale": "Web search surfaces job postings from company websites and permitted boards. RSS feeds from tech job boards provide structured listings.",
        },
        "dag": [
            {"id": "n1", "type": "discover_sources", "depends_on": [], "params": {}, "label": "Discover Sources"},
            {"id": "n2", "type": "fetch", "depends_on": ["n1"], "params": {}, "label": "Fetch Pages"},
            {"id": "n3", "type": "extract", "depends_on": ["n2"], "params": {}, "label": "Extract Listings"},
            {"id": "n4", "type": "normalize", "depends_on": ["n3"], "params": {}, "label": "Normalize"},
            {"id": "n5", "type": "validate", "depends_on": ["n4"], "params": {}, "label": "Validate"},
            {"id": "n6", "type": "dedupe", "depends_on": ["n5"], "params": {}, "label": "Deduplicate"},
            {"id": "n7", "type": "score", "depends_on": ["n6"], "params": {}, "label": "Score"},
            {"id": "n8", "type": "finalize", "depends_on": ["n7"], "params": {}, "label": "Finalize"},
        ],
        "limits": {"max_pages": 25, "max_records": 40, "per_domain_rps": 1.0},
        "assumptions": ["Targeting internships posted in the last 3 months.", "Remote positions only."],
        "clarifying_questions": ["Should I include part-time internships or only full-time?"],
        "risk_notes": ["LinkedIn job postings require login; excluded.", "Indeed requires specific API access; excluded."],
    }


def _repos_spec() -> dict:
    return {
        "title": "Open-Source ML GitHub Repositories",
        "intent_summary": "Collect popular open-source machine learning repositories from GitHub with metadata for analysis.",
        "entity_type": "github_repo",
        "fields": [
            {"name": "repo_name", "label": "Repository Name", "type": "string", "description": "Full repo name (owner/repo)", "required": True, "unique_key": True, "validators": []},
            {"name": "owner", "label": "Owner", "type": "string", "description": "GitHub username or organization", "required": True, "unique_key": False, "validators": []},
            {"name": "stars", "label": "Stars", "type": "integer", "description": "Number of GitHub stars", "required": False, "unique_key": False, "validators": []},
            {"name": "description", "label": "Description", "type": "string", "description": "Repository description from GitHub", "required": False, "unique_key": False, "validators": []},
            {"name": "language", "label": "Primary Language", "type": "string", "description": "Main programming language", "required": False, "unique_key": False, "validators": []},
            {"name": "license", "label": "License", "type": "string", "description": "Open-source license type (MIT, Apache 2.0, etc.)", "required": False, "unique_key": False, "validators": []},
            {"name": "url", "label": "Repository URL", "type": "url", "description": "Full GitHub URL to the repository", "required": True, "unique_key": False, "validators": ["url"]},
            {"name": "last_updated", "label": "Last Updated", "type": "date", "description": "Date of last commit or release", "required": False, "unique_key": False, "validators": []},
        ],
        "source_strategy": {
            "connectors": ["github", "web_search"],
            "seed_queries": [
                "machine learning framework python stars:>1000",
                "deep learning library open source",
                "natural language processing python",
            ],
            "seed_urls": [],
            "domain_allowlist": ["github.com"],
            "domain_blocklist": [],
            "rationale": "GitHub public search API provides structured repo data. Web search supplements with curated ML repo lists.",
        },
        "dag": [
            {"id": "n1", "type": "discover_sources", "depends_on": [], "params": {}, "label": "Discover Repos"},
            {"id": "n2", "type": "fetch", "depends_on": ["n1"], "params": {}, "label": "Fetch Pages"},
            {"id": "n3", "type": "extract", "depends_on": ["n2"], "params": {}, "label": "Extract Data"},
            {"id": "n4", "type": "normalize", "depends_on": ["n3"], "params": {}, "label": "Normalize"},
            {"id": "n5", "type": "dedupe", "depends_on": ["n4"], "params": {}, "label": "Deduplicate"},
            {"id": "n6", "type": "score", "depends_on": ["n5"], "params": {}, "label": "Score"},
            {"id": "n7", "type": "finalize", "depends_on": ["n6"], "params": {}, "label": "Finalize"},
        ],
        "limits": {"max_pages": 20, "max_records": 50, "per_domain_rps": 0.5},
        "assumptions": ["Filtering repositories with >100 stars.", "Python or PyTorch-based repos prioritized."],
        "clarifying_questions": [],
        "risk_notes": ["GitHub API is rate-limited to 10 requests/minute without authentication."],
    }


def _arxiv_spec() -> dict:
    return {
        "title": "Recent arXiv Papers on RAG",
        "intent_summary": "Collect recent research papers on Retrieval-Augmented Generation (RAG) from arXiv with abstracts and author information.",
        "entity_type": "research_paper",
        "fields": [
            {"name": "title", "label": "Paper Title", "type": "string", "description": "Full title of the paper", "required": True, "unique_key": True, "validators": ["min_len:5"]},
            {"name": "authors", "label": "Authors", "type": "string", "description": "Comma-separated list of author names", "required": True, "unique_key": False, "validators": []},
            {"name": "abstract", "label": "Abstract", "type": "string", "description": "Paper abstract summarizing the contribution", "required": False, "unique_key": False, "validators": []},
            {"name": "arxiv_url", "label": "arXiv URL", "type": "url", "description": "Direct link to the arXiv abstract page", "required": True, "unique_key": False, "validators": ["url"]},
            {"name": "published_date", "label": "Published Date", "type": "date", "description": "Date paper was submitted to arXiv", "required": False, "unique_key": False, "validators": []},
            {"name": "primary_category", "label": "Category", "type": "string", "description": "arXiv primary category (e.g. cs.CL, cs.IR)", "required": False, "unique_key": False, "validators": []},
        ],
        "source_strategy": {
            "connectors": ["arxiv", "web_search"],
            "seed_queries": [
                "retrieval augmented generation RAG",
                "RAG large language model question answering",
                "knowledge retrieval LLM grounding",
            ],
            "seed_urls": [],
            "domain_allowlist": ["arxiv.org"],
            "domain_blocklist": [],
            "rationale": "arXiv public API is the primary source for academic papers. Web search supplements with survey papers and blog posts linking to papers.",
        },
        "dag": [
            {"id": "n1", "type": "discover_sources", "depends_on": [], "params": {}, "label": "Search arXiv"},
            {"id": "n2", "type": "fetch", "depends_on": ["n1"], "params": {}, "label": "Fetch Abstracts"},
            {"id": "n3", "type": "extract", "depends_on": ["n2"], "params": {}, "label": "Extract Metadata"},
            {"id": "n4", "type": "normalize", "depends_on": ["n3"], "params": {}, "label": "Normalize Dates"},
            {"id": "n5", "type": "dedupe", "depends_on": ["n4"], "params": {}, "label": "Deduplicate"},
            {"id": "n6", "type": "score", "depends_on": ["n5"], "params": {}, "label": "Score"},
            {"id": "n7", "type": "finalize", "depends_on": ["n6"], "params": {}, "label": "Finalize"},
        ],
        "limits": {"max_pages": 20, "max_records": 30, "per_domain_rps": 2.0},
        "assumptions": ["Filtering papers from the last 12 months.", "Focusing on NLP/AI categories."],
        "clarifying_questions": [],
        "risk_notes": ["arXiv API has generous rate limits for non-commercial use."],
    }


def _news_spec() -> dict:
    return {
        "title": "Tech Newsletter Sponsorship Opportunities",
        "intent_summary": "Collect information about tech newsletters that accept paid sponsorships, including audience size and pricing.",
        "entity_type": "sponsorship_opportunity",
        "fields": [
            {"name": "newsletter_name", "label": "Newsletter Name", "type": "string", "description": "Name of the newsletter or publication", "required": True, "unique_key": True, "validators": ["min_len:2"]},
            {"name": "audience_size", "label": "Audience Size", "type": "string", "description": "Number of subscribers (e.g. '50,000 subscribers')", "required": False, "unique_key": False, "validators": []},
            {"name": "niche", "label": "Niche/Topic", "type": "string", "description": "Primary topic area (e.g. AI, DevOps, Frontend)", "required": False, "unique_key": False, "validators": []},
            {"name": "pricing", "label": "Sponsorship Pricing", "type": "currency", "description": "Sponsorship cost per issue or per month", "required": False, "unique_key": False, "validators": []},
            {"name": "contact_email", "label": "Contact Email", "type": "email", "description": "Email for sponsorship inquiries", "required": False, "unique_key": False, "validators": ["email"]},
            {"name": "url", "label": "Newsletter URL", "type": "url", "description": "Homepage or sponsorship page URL", "required": True, "unique_key": False, "validators": ["url"]},
        ],
        "source_strategy": {
            "connectors": ["web_search", "rss"],
            "seed_queries": [
                "tech newsletter sponsorship advertise with us",
                "developer newsletter sponsor pricing media kit",
                "AI newsletter advertising opportunities subscribers",
            ],
            "seed_urls": [],
            "domain_allowlist": [],
            "domain_blocklist": [],
            "rationale": "Web search finds sponsorship pages and media kits. RSS helps discover active newsletters.",
        },
        "dag": [
            {"id": "n1", "type": "discover_sources", "depends_on": [], "params": {}, "label": "Discover Sources"},
            {"id": "n2", "type": "fetch", "depends_on": ["n1"], "params": {}, "label": "Fetch Pages"},
            {"id": "n3", "type": "extract", "depends_on": ["n2"], "params": {}, "label": "Extract Data"},
            {"id": "n4", "type": "normalize", "depends_on": ["n3"], "params": {}, "label": "Normalize"},
            {"id": "n5", "type": "validate", "depends_on": ["n4"], "params": {}, "label": "Validate"},
            {"id": "n6", "type": "dedupe", "depends_on": ["n5"], "params": {}, "label": "Deduplicate"},
            {"id": "n7", "type": "score", "depends_on": ["n6"], "params": {}, "label": "Score"},
            {"id": "n8", "type": "finalize", "depends_on": ["n7"], "params": {}, "label": "Finalize"},
        ],
        "limits": {"max_pages": 25, "max_records": 30, "per_domain_rps": 1.0},
        "assumptions": ["Targeting newsletters with >5,000 subscribers.", "Tech/developer audience only."],
        "clarifying_questions": ["What is your monthly budget for newsletter sponsorships?"],
        "risk_notes": ["Some newsletter sponsorship info may be behind media kit request forms."],
    }


_FIXTURE_MAP = {
    "startup": _startup_spec,
    "jobs": _jobs_spec,
    "repos": _repos_spec,
    "arxiv": _arxiv_spec,
    "news": _news_spec,
}

_KEYWORD_MAP = {
    "startup": ["startup", "company", "india", "founder", "venture", "funding"],
    "jobs": ["job", "internship", "hiring", "career", "position", "intern", "remote"],
    "repos": ["repo", "github", "repository", "open source", "library", "framework"],
    "arxiv": ["arxiv", "paper", "research", "rag", "retrieval", "academic", "llm"],
    "news": ["newsletter", "sponsor", "advertising", "media kit", "publication"],
}


def _detect_fixture_type(user: str) -> str:
    user_lower = user.lower()
    scores = {k: sum(1 for kw in keywords if kw in user_lower) for k, keywords in _KEYWORD_MAP.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "news"


class MockLLMClient:
    """
    Deterministic mock LLM client.
    Returns realistic WorkflowSpec fixtures based on prompt keywords.
    No randomness — results are repeatable for tests and demos.
    """

    async def complete_json(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        max_retries: int = 2,
    ) -> BaseModel:
        # Import lazily to avoid circular imports
        from app.schemas.workflow import WorkflowSpec

        if schema is WorkflowSpec:
            fixture_type = _detect_fixture_type(user)
            spec_dict = _FIXTURE_MAP[fixture_type]()
            return WorkflowSpec.model_validate(spec_dict)

        # For extraction responses — return a minimal valid structure
        # Use hash of input for determinism
        h = hashlib.md5(user.encode()).hexdigest()[:6]

        # Try to create a valid instance by inspecting the schema fields
        try:
            # ExtractionResponse has a "records" field
            if hasattr(schema, "model_fields") and "records" in schema.model_fields:
                return schema.model_validate({"records": []})
        except Exception:
            pass

        # Fallback: return empty schema
        try:
            return schema.model_validate({})
        except Exception:
            return schema.model_validate({"result": f"mock_{h}"})
