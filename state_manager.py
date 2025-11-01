import json
import os

STATE_FILE_TEMPLATE = "{project_key}_state.json"

def load_state(project_key):
    """Loads the last successful 'startAt' index for the project."""
    state_file = STATE_FILE_TEMPLATE.format(project_key=project_key)
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                return state.get("startAt", 0)
        except json.JSONDecodeError:
            print(f"Warning: State file {state_file} is corrupt. Starting from 0.")
            return 0
    return 0

def save_state(project_key, start_at):
    """Saves the *next* 'startAt' index to process."""
    state_file = STATE_FILE_TEMPLATE.format(project_key=project_key)
    with open(state_file, 'w') as f:
        json.dump({"startAt": start_at}, f)