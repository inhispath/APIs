import os

BASE_DB_PATH = os.path.join("bible_databases", "formats", "sqlite")

# Iterate over the files in the specified directory
for filename in os.listdir(BASE_DB_PATH):
    # Get the full path of the file
    old_file_path = os.path.join(BASE_DB_PATH, filename)
    
    # Check if it is a file (and not a directory)
    if os.path.isfile(old_file_path):
        # Split the file name and extension
        file_name, file_extension = os.path.splitext(filename)
        
        # Convert the file name to uppercase, but keep the extension intact
        new_file_name = file_name.upper() + file_extension
        
        # Get the full path for the new file name
        new_file_path = os.path.join(BASE_DB_PATH, new_file_name)
        
        # Rename the file
        os.rename(old_file_path, new_file_path)
        print(f"Renamed: {filename} -> {new_file_name}")
