import os
import shutil

# Base directory for the databases (same as in main.py)
BASE_DB_PATH = os.path.join("bible_databases", "formats", "sqlite")

def rename_to_uppercase():
    """Rename all files in the sqlite directory to uppercase."""
    if not os.path.exists(BASE_DB_PATH):
        print(f"Directory {BASE_DB_PATH} does not exist.")
        return
    
    for filename in os.listdir(BASE_DB_PATH):
        if filename.endswith(".db"):
            # Get the full paths
            old_path = os.path.join(BASE_DB_PATH, filename)
            new_filename = filename.upper()
            new_path = os.path.join(BASE_DB_PATH, new_filename)
            
            # Skip if the file is already uppercase
            if filename == new_filename:
                print(f"File {filename} is already uppercase. Skipping.")
                continue
            
            # Check for case conflicts (Windows is case-insensitive)
            if os.path.exists(new_path) and old_path.lower() != new_path.lower():
                print(f"Warning: Cannot rename {filename} to {new_filename} - file already exists.")
                continue
                
            try:
                # Rename the file
                shutil.move(old_path, new_path)
                print(f"Renamed {filename} → {new_filename}")
            except Exception as e:
                print(f"Error renaming {filename}: {e}")

if __name__ == "__main__":
    rename_to_uppercase()
    print("Renaming complete.") 