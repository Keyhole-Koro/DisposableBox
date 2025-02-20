import os
import json

class Settings:
    def __init__(self):
        self.settings_file = "container_manager_settings.json"
        self.settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                return {"last_iso_path": ""}
        return {"last_iso_path": ""}

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f)

    def get_last_iso_path(self):
        return self.settings.get("last_iso_path", "")

    def set_last_iso_path(self, path):
        self.settings["last_iso_path"] = path
        self.save_settings()
