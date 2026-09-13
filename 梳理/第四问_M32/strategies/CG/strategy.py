from cautious import Planner
import json
from pathlib import Path
VERSION='p4-literature-cautious-beta005-v1'
POLICIES=json.loads(Path(__file__).with_name('policies.json').read_text(encoding='utf-8'))
