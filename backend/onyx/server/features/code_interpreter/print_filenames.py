"""
Utility module to print dataset filenames clearly for debugging
"""
import sys

def print_dataset_filenames(dataset_names, filenames):
    """Print dataset filenames to stdout and stderr"""
    print("\n### Dataset Files ###")
    print(f"Dataset Names: {dataset_names}")
    print(f"Actual Filenames: {filenames}")
    
    # Print to stderr as well to ensure visibility
    sys.stderr.write(f"\nDataset Names: {dataset_names}\n")
    sys.stderr.write(f"Actual Filenames: {filenames}\n")
    
    # Write to log file
    try:
        with open("/tmp/dataset_filenames.log", "a") as f:
                f.write(f"Dataset Names: {dataset_names}\n")
                f.write(f"Actual Filenames: {filenames}\n")
                
                # Create a mapping for easy reference
                if len(dataset_names) == len(filenames):
                    f.write("\nMAPPING:\n")
                    for dataset, filename in zip(dataset_names, filenames):
                        f.write(f"{dataset} → {filename}\n")
    except Exception:
        pass 