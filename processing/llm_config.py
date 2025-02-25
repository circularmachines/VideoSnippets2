"""Konfiguration och schema för LLM-interaktioner vid produktindexering."""

from typing import List
from pydantic import BaseModel, Field

# Model configuration
MODEL = "gpt-4o"

# System message for the LLM
SYSTEM_MESSAGE = """Du är en expert på att analysera videor av begagnade produkter. Din uppgift är att skapa meningsfulla snippets som beskriver produkterna som visas.

En snippet är en grupp av segment som hör ihop tematiskt och beskriver:
1. En specifik produkt eller produktgrupp som visas
2. Produktens skick och egenskaper
3. Eventuella detaljer om användning eller installation

För varje snippet ska du:
1. Ge den en tydlig titel som beskriver produkten
2. Skriv en detaljerad beskrivning som inkluderar:
   - Vad det är för produkt
   - Skick och särskilda kännetecken
   - Relevant kontext från videon
3. Lista vilka segment som tillhör snippeten (använd segmentnummer från input)

Fokusera på detaljer som är viktiga för någon som letar efter begagnade produkter."""

# Prompt templates
PROMPTS = {
    "language_suffix": "",
    "user_prompt": "{text}"
}

class Snippet(BaseModel):
    """En snippet representerar en tematisk grupp av videosegment."""
    title: str = Field(
        description="Koncis titel som beskriver produkten eller produktgruppen"
    )
    description: str = Field(
        description="Detaljerad beskrivning av produkten, dess skick och kontext"
    )
    segments: List[int] = Field(
        description="Lista över segmentindex som tillhör denna snippet"
    )
    product_type: str = Field(
        description="Produktkategori (t.ex. 'Verktyg', 'Cykeldelar', 'Elektronik')"
    )
    condition: str = Field(
        description="Produktens skick (t.ex. 'Nyskick', 'Begagnad', 'Defekt', 'Renoveringsobjekt')"
    )
    brand: str | None = Field(
        description="Varumärke om det nämns eller syns i videon",
        default=None
    )
    compatibility: str | None = Field(
        description="Information om kompatibilitet eller passform",
        default=None
    )
    modifications: List[str] = Field(
        description="Lista över modifieringar eller reparationer som gjorts",
        default_factory=list
    )
    missing_parts: List[str] = Field(
        description="Lista över delar som saknas eller behöver åtgärdas",
        default_factory=list
    )
    intended_use: str | None = Field(
        description="Tänkt användningsområde eller installation",
        default=None
    )

class SnippetsResponse(BaseModel):
    """Svarsformat för snippetgenerering."""
    snippets: List[Snippet] = Field(
        description="Lista över snippets genererade från videoinnehållet"
    )
