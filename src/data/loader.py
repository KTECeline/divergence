"""Load and parse the raw MalSkillBench dataset into SkillSample objects.

Build order item 2. Blocked until the dataset is placed in
data/raw/malskillbench/ — inspect its actual format first, then implement.
"""

from src.config import RAW_MALSKILLBENCH_DIR
from src.data.schema import SkillSample


def load_malskillbench() -> list[SkillSample]:
    """Parse the raw MalSkillBench files into a list of SkillSample."""
    raise NotImplementedError(
        f"Implement once the dataset is available in {RAW_MALSKILLBENCH_DIR}"
    )
