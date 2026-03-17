import enum
import logging

logger = logging.getLogger(__name__)

DEFAULT_OCR_PROMPT = """You are analyzing PNG images of handwritten text from an \
e-ink notebook SuperNote. The notes are written in English and are in a \
bullet journal format. You can see that the text is not perfect and will need \
some cleaning up

Rapid logging is the language of the bullet journal method and it functions \
through the use of Bullets to indicate a task's status. A task starts with a simple \
dot "•" to represent a task. If a task is completed, mark it with an "X". If it's \
migrated to a future date, use a right arrow (>) to indicate that. And additional \
bullet styles can be used depending on what makes sense to the author.

Tasks within the Bullet Journal method can then fall within any of the logs used \
depending on where they fall in the author's timeline. Typically, journals contain \
a Daily Log, Weekly Log, and Monthly Log."""

DEFAULT_SUMMARY_COMMON_PROMPT = """You are an expert assistant helping to digitize \
and summarize a handwritten Bullet Journal.
You must extract a list of `SummarySegment` objects.
Each segment should represent a logical unit of time or topic \
(e.g. a single day, a week, a project).
Extract any specific dates mentioned in the segment in ISO 8601 format (YYYY-MM-DD).
Cite the page numbers (e.g. 1, 2) that contributed to each segment \
based on the `--- Page X ---` markers.

The input text is an OCR transcript of handwritten notes. It may contain errors or noise.
Do your best to infer the correct meaningful content."""

DEFAULT_SUMMARY_PROMPT = """Summarise the content of these notes, extracting \
key topics, any tasks or action items, and important events or decisions."""


class PromptId(str, enum.Enum):
    OCR_TRANSCRIPTION = "ocr_transcription"
    SUMMARY_GENERATION = "summary_generation"


CATEGORY_MAP = {
    "ocr": PromptId.OCR_TRANSCRIPTION.value,
    "summary": PromptId.SUMMARY_GENERATION.value,
}
COMMON = "common"
DEFAULT = "default"

# Layers that are always present and cannot be removed via the API
PROTECTED_LAYERS: frozenset[tuple[str, str]] = frozenset(
    {("ocr", DEFAULT), ("summary", DEFAULT), ("summary", COMMON)}
)


class PromptLoader:
    """Provides default prompts used when no user override is configured."""

    def __init__(self) -> None:
        self.prompts: dict[str, dict[str, str]] = {
            PromptId.OCR_TRANSCRIPTION.value: {
                DEFAULT: DEFAULT_OCR_PROMPT,
            },
            PromptId.SUMMARY_GENERATION.value: {
                COMMON: DEFAULT_SUMMARY_COMMON_PROMPT,
                DEFAULT: DEFAULT_SUMMARY_PROMPT,
            },
        }

    def get_all_known_layers(self) -> dict[str, dict[str, str]]:
        """Return all default layers keyed by prompt_id value then layer name."""
        return {pid: dict(layers) for pid, layers in self.prompts.items()}

    def get_prompt(self, prompt_id: PromptId, custom_type: str | None = None) -> str:
        """Return the composed default prompt for the given prompt_id.

        Composes common (if present) + default. custom_type is accepted for API
        compatibility but ignored — custom prompts are managed via
        PromptConfigService (DB overrides), not the loader.
        """
        key = prompt_id.value if isinstance(prompt_id, PromptId) else str(prompt_id)
        type_map = self.prompts.get(key)
        if not type_map:
            raise ValueError(f"Prompt ID '{prompt_id}' not found.")
        parts = []
        if COMMON in type_map:
            parts.append(type_map[COMMON])
        if DEFAULT in type_map:
            parts.append(type_map[DEFAULT])
        return "\n\n".join(parts)


PROMPT_LOADER = PromptLoader()
