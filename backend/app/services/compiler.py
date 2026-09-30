import json

STARTUP_SCHEMA = [
    {"name": "name", "type": "string", "required": True, "description": "Company name"},
    {"name": "founders", "type": "string", "required": True, "description": "Founder names (comma-separated)"},
    {"name": "funding_amount", "type": "string", "required": False, "description": "Funding amount and round (e.g. $41M Series A)"},
    {"name": "location", "type": "string", "required": False, "description": "City and country of headquarters"},
    {"name": "career_page_url", "type": "url", "required": False, "description": "Link to careers/jobs page"},
    {"name": "description", "type": "string", "required": False, "description": "One-line company description"},
]

HACKATHON_SCHEMA = [
    {"name": "event_name", "type": "string", "required": True, "description": "Name of the hackathon or event"},
    {"name": "date", "type": "date", "required": True, "description": "Event start and end dates"},
    {"name": "location", "type": "string", "required": False, "description": "City/state or 'Online'"},
    {"name": "prize_pool", "type": "string", "required": False, "description": "Total prize money available"},
    {"name": "registration_url", "type": "url", "required": False, "description": "Registration or signup link"},
    {"name": "organizer", "type": "string", "required": False, "description": "Organizing company or individual"},
]

SAAS_SCHEMA = [
    {"name": "company_name", "type": "string", "required": True, "description": "Name of the SaaS company"},
    {"name": "website", "type": "url", "required": True, "description": "Company website URL"},
    {"name": "pricing_tier", "type": "string", "required": False, "description": "Pricing plans and costs"},
    {"name": "features", "type": "string", "required": False, "description": "Key product features"},
    {"name": "contact_email", "type": "email", "required": False, "description": "Sales or support email"},
    {"name": "category", "type": "string", "required": False, "description": "Product category (e.g. Productivity)"},
]

DEFAULT_SCHEMA = [
    {"name": "title", "type": "string", "required": True, "description": "Title or heading"},
    {"name": "description", "type": "string", "required": False, "description": "Summary or body text"},
    {"name": "url", "type": "url", "required": False, "description": "Source URL"},
    {"name": "date", "type": "date", "required": False, "description": "Publication or event date"},
    {"name": "category", "type": "string", "required": False, "description": "Content category"},
]

EXECUTION_DAG = [
    {"step": 1, "name": "Query Construction", "description": "Build search queries from the prompt intent and target schema fields", "status": "pending"},
    {"step": 2, "name": "Source Discovery", "description": "Discover permitted public URLs and verify robots.txt compliance", "status": "pending"},
    {"step": 3, "name": "Page Retrieval", "description": "Fetch pages, strip navigation/scripts, convert HTML to clean Markdown", "status": "pending"},
    {"step": 4, "name": "Entity Extraction", "description": "Run structured extraction against target schema using LLM + regex fallback", "status": "pending"},
    {"step": 5, "name": "Deduplication & Validation", "description": "Deduplicate records by primary key, validate types, compute confidence scores", "status": "pending"},
]


def compile_workflow(prompt: str, use_mock: bool = True) -> tuple[str, str]:
    prompt_lower = prompt.lower()

    if "startup" in prompt_lower or "company" in prompt_lower or "india" in prompt_lower:
        schema = STARTUP_SCHEMA
    elif "hackathon" in prompt_lower or "event" in prompt_lower or "conference" in prompt_lower:
        schema = HACKATHON_SCHEMA
    elif "lead" in prompt_lower or "saas" in prompt_lower or "software" in prompt_lower or "directory" in prompt_lower:
        schema = SAAS_SCHEMA
    else:
        schema = DEFAULT_SCHEMA

    return json.dumps(schema), json.dumps(EXECUTION_DAG)
