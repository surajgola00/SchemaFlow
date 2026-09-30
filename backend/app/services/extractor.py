# Extractor service mock
async def extract_entities(content: str, schema: list, use_mock: bool = True) -> list:
    if use_mock:
        return []
    return []
