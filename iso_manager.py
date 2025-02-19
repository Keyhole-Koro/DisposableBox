import os

class ISOManager:
    def __init__(self, settings):
        self.settings = settings
        self.iso_dir = os.path.join(os.path.expanduser("~"), "container_isos")
        os.makedirs(self.iso_dir, exist_ok=True)
    
    def get_iso_list(self):
        isos = []
        for file in os.listdir(self.iso_dir):
            if file.endswith('.iso'):
                isos.append(os.path.join(self.iso_dir, file))
        return isos
    
    def import_iso(self, source_path):
        dest_path = os.path.join(self.iso_dir, os.path.basename(source_path))
        if not os.path.exists(dest_path):
            import shutil
            shutil.copy2(source_path, dest_path)
        return dest_path
