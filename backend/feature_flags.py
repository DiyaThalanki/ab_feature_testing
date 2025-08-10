import json
import os

FLAGS_PATH = os.path.join(os.path.dirname(__file__), "feature_flags.json")

def get_flags():
    with open(FLAGS_PATH) as f:
        return json.load(f)
