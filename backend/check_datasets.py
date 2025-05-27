"""
Script to check datasets and their connectors
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from onyx.db.models import Dataset, ConnectorCredentialPair, Connector
import os

def main():
    # Connect to the database
    engine = create_engine('postgresql://postgres:password@localhost:5432/postgres')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Query all datasets
    datasets = session.query(Dataset).all()
    print(f"Found {len(datasets)} datasets:")
    
    # Print dataset info
    for dataset in datasets:
        print(f"\n{'='*50}")
        print(f"DATASET: {dataset.name} (ID: {dataset.id})")
        print(f"{'='*50}")
        
        # Get connector-credential pairs for this dataset
        cc_pairs = dataset.connector_credential_pairs
        
        # Print connector info
        for cc_pair in cc_pairs:
            connector = cc_pair.connector
            print(f"Connector: {connector.name} (type: {connector.source})")
            
            # Print connector config
            if connector.connector_specific_config:
                config = connector.connector_specific_config
                
                # For file connectors
                if connector.source == "file" or connector.source == "DocumentSource.FILE":
                    # Try different possible file path keys
                    file_paths = []
                    if "file_paths" in config:
                        file_paths = config["file_paths"]
                    elif "file_locations" in config:
                        file_paths = config["file_locations"]
                    
                    print("\nACTUAL FILES IN THIS DATASET:")
                    for file_path in file_paths:
                        # Extract just the filename from the path
                        filename = os.path.basename(file_path)
                        print(f"  → {filename}")
                        
                        # Print this in a format that's easy to copy-paste
                        print(f"\nWhen using dataset '{dataset.name}', you should use filename: '{filename}'")
                        print(f"Example code: df = pd.read_csv('/datasets/{filename}')")

if __name__ == "__main__":
    main() 