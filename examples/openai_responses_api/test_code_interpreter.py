#!/usr/bin/env python3
"""
Sample test application for OpenAI Responses API with Code Interpreter
Tests the basic functionality of uploading files and running code in OpenAI's sandbox.
"""

import os
import tempfile
import pandas as pd
from openai import OpenAI
from typing import Optional
def create_sample_data_file() -> str:
    """Create a sample CSV file for testing"""
    # Create sample data
    data = {
        'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'age': [25, 30, 35, 28, 32],
        'salary': [50000, 60000, 70000, 55000, 65000],
        'department': ['Engineering', 'Marketing', 'Engineering', 'HR', 'Marketing']
    }
    
    df = pd.DataFrame(data)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        df.to_csv(f.name, index=False)
        return f.name


def upload_file_to_openai(client: OpenAI, file_path: str) -> str:
    """Upload a file to OpenAI and return the file ID"""
    print(f"Uploading file: {file_path}")
    
    with open(file_path, 'rb') as file:
        uploaded_file = client.files.create(
            file=file,
            purpose='assistants'  # Code Interpreter uses 'assistants' purpose
        )
    
    print(f"File uploaded successfully! File ID: {uploaded_file.id}")
    print(f"File size: {uploaded_file.bytes} bytes")
    print(f"Filename: {uploaded_file.filename}")
    return uploaded_file.id


def upload_brixadi_dataset(client: OpenAI) -> str:
    """Upload the BRIXADI ATU WAVE 3-test.xlsx file and return the file ID"""
    # Try multiple possible locations for the BRIXADI dataset file
    possible_paths = [
        "../../datasets/BRIXADI ATU WAVE 3-test.xlsx",  # Updated location
        "./BRIXADI ATU WAVE 3-test.xlsx",  # Current directory
        "./datasets/BRIXADI ATU WAVE 3-test.xlsx",  # Local datasets folder
    ]
    
    dataset_path = None
    for path in possible_paths:
        if os.path.exists(path):
            dataset_path = path
            break
    
    if not dataset_path:
        raise FileNotFoundError(f"BRIXADI dataset file not found. Tried locations: {possible_paths}")
    
    print(f"Found BRIXADI dataset file: {dataset_path}")
    file_size = os.path.getsize(dataset_path)
    print(f"File size: {file_size} bytes ({file_size/1024:.1f} KB)")
    
    return upload_file_to_openai(client, dataset_path)


def test_brixadi_awareness_analysis(client: OpenAI, file_id: str) -> None:
    """Test BRIXADI awareness analysis using the uploaded Excel file"""
    print(f"Testing BRIXADI awareness analysis with file ID: {file_id}")
    
    user_query = """In this analysis, use the Data Map tab to understand the A1 tab. 
    Now answer, what was aided awareness of brixadi based on question a4 in Wave 3? give me the total % and 
    then breakdowns for each specialty but I want my specialty analysis to be by PCP/GP/IM, Psych, Add Spec, NP or PA, 
    and then rest as "Other" please. 
    Explain your rationale and reasoning for each calculation you do to allow the user to assess the validity and always show all of your work to all for human quality control.
    """
    
    # Create response using Responses API with Code Interpreter
    response = client.responses.create(
        model="o3",
        tools=[
            {
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": [file_id]
                }
            }
        ],
            instructions="""You are an expert data analyst specializing in pharmaceutical market research and survey analysis. 
            Use the code interpreter tool to run python code with the uploaded file for answering the question
            """,
        input=user_query
    )
    
    print("\n=== BRIXADI Awareness Analysis Results ===")
    print(response.output[-1].content[0].text)
    print("--------------------------------")
    print(response.output_text)
    
    # Check for generated files
    if hasattr(response, 'messages'):
        for message in response.messages:
            if hasattr(message, 'content'):
                for content in message.content:
                    if hasattr(content, 'annotations'):
                        for annotation in content.annotations:
                            if annotation.type == 'container_file_citation':
                                print(f"\nGenerated file: {annotation.filename}")
                                print(f"File ID: {annotation.file_id}")


def test_code_interpreter_with_file(client: OpenAI, file_id: str) -> None:
    """Test Code Interpreter with uploaded file using Responses API"""
    print(f"Testing Code Interpreter with file ID: {file_id}")
    
    # Create response using Responses API with Code Interpreter
    response = client.responses.create(
        model="gpt-4o",
        tools=[
            {
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "file_ids": [file_id]  # Include the uploaded file
                }
            }
        ],
        instructions="You are a data analyst. Use the uploaded file to analyze the data and create visualizations.",
        input="Please analyze the uploaded employee data CSV file. Calculate basic statistics, create a visualization showing salary distribution by department, and provide insights about the data."
    )
    
    print("\n=== Code Interpreter Response ===")
    print(response.output_text)
    
    # Check if any files were created by the code interpreter
    if hasattr(response, 'messages'):
        for message in response.messages:
            if hasattr(message, 'content'):
                for content in message.content:
                    if hasattr(content, 'annotations'):
                        for annotation in content.annotations:
                            if annotation.type == 'container_file_citation':
                                print(f"\nGenerated file: {annotation.filename}")
                                print(f"File ID: {annotation.file_id}")
                                print(f"Container ID: {annotation.container_id}")


def test_simple_code_interpreter(client: OpenAI) -> None:
    """Test basic Code Interpreter functionality without files"""
    print("Testing basic Code Interpreter functionality...")
    
    response = client.responses.create(
        model="gpt-4o",
        tools=[
            {
                "type": "code_interpreter",
                "container": {"type": "auto"}
            }
        ],
        instructions="You are a math tutor. Use Python to solve problems step by step.",
        input="Calculate the square root of 2 raised to the power of 10, then plot a sine wave from 0 to 2π. Show your work."
    )
    
    print("\n=== Basic Code Interpreter Response ===")
    print(response.output_text)


def test_with_existing_file_id(client: OpenAI, file_id: str) -> None:
    """Test analysis using an existing file ID (no upload needed)"""
    print(f"Testing with existing BRIXADI file ID: {file_id}")
    
    # Verify the file exists
    try:
        file_info = client.files.retrieve(file_id)
        print(f"File verified: {file_info.filename} ({file_info.bytes} bytes)")
    except Exception as e:
        print(f"Error: Could not retrieve file with ID {file_id}: {str(e)}")
        return
    
    # Run the BRIXADI analysis
    test_brixadi_awareness_analysis(client, file_id)


def main():
    """Main function to run all tests"""
    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set")
        return
    
    client = OpenAI(api_key=api_key)
    
    print("🚀 Testing OpenAI Responses API with Code Interpreter")
    print("=" * 60)
    
    # Option to use existing file ID (set this if you already have a file uploaded)
    existing_file_id = "file-HJY7jM3mJVK8vey6bQ67eF"  # BRIXADI file ID from previous upload
    # Example: existing_file_id = "file-abc123xyz"
    
    try:
        if existing_file_id:
            print(f"\n📁 Using existing BRIXADI file ID: {existing_file_id}")
            test_with_existing_file_id(client, existing_file_id)
        else:
            print("\n📁 Uploading BRIXADI dataset and running analysis")
            
            # Upload BRIXADI dataset
            brixadi_file_id = upload_brixadi_dataset(client)
            print(f"✅ BRIXADI file uploaded with ID: {brixadi_file_id}")
            print("💡 For future tests, you can use this file ID directly by setting:")
            print(f"    existing_file_id = '{brixadi_file_id}'")
            
            # Run the BRIXADI awareness analysis
            test_brixadi_awareness_analysis(client, brixadi_file_id)
            
            print(f"\n🗑️  Note: File {brixadi_file_id} is still available on OpenAI for future use")
            print("    You can delete it manually if needed using: client.files.delete(file_id)")
    
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        raise


if __name__ == "__main__":
    main() 