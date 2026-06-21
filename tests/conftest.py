"""pytest conftest — zajistí, že sandbox root je na sys.path pro `import server.cage.*`."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
