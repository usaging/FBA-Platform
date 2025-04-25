import cobra
import pandas as pd
import json
from pathlib import Path



# 使用示例
if __name__ == "__main__":
    export_reactions_json(
        model_path="path/to/model.xml",
        rxn_csv_path="rxn.csv",
        output_json_path="reactions.json"
    )