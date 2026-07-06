from dataclasses import dataclass


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    file_name: str
    pages: list[PageText]
    mime_type: str | None = None

    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)

