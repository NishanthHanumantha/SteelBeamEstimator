import json
from src.extractor.detail_validator import validate_detail_blocks

blocks = json.load(open("data/output/reinforcement_detail_blocks.json"))
v = validate_detail_blocks(blocks)
print("passed:", v["passed"])
for x in v["violations"]:
    print(x)
