import os
import sys
import glob

def concatenate_files(source_path, target_path):
    # Use the exact pattern: **/*/*/*/*.gold_skel (3 levels deep)
    pattern = os.path.join(source_path, "**", "*", "*", "*.gold_skel")
    print(pattern)
    # Find all matching .gold_skel files
    file_paths = glob.glob(pattern, recursive=True)
    
    if not file_paths:
        print("No .gold_skel files found in the specified directory.")
        return
    
    try:
        # Open the target file for appending (similar to `>>` in shell)
        with open(target_path, "a") as target_file:
            for file_path in file_paths:
                # Read each .gold_skel file and write its content to the target
                with open(file_path, "r") as source_file:
                    content = source_file.read()
                    target_file.write(content)
        
        print(f"Successfully concatenated {len(file_paths)} files into {target_path}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python concatenate_gold_skel.py <source_directory> <target_file>")
        sys.exit(1)
    
    source_path = sys.argv[1]
    target_path = sys.argv[2]
    
    # Ensure the source path ends with a separator
    if not source_path.endswith(os.sep):
        source_path += os.sep
    
    concatenate_files(source_path, target_path)
