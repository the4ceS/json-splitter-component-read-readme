import json
from pathlib import Path

    #param input_file: Path to the input JSON file.
    #param output_dir: Directory to save the split files.

input_file = r"D:\Users\4ceS\Desktop\fastpermits\RAG\Abilene-Texas.json"
output_dir = "./output"

def split_json_and_add_metadata(input_file, output_dir):
#Splits a JSON file into components and attaches metadata for articles and subsections.
    
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Process the JSON data
    for idx, entry in enumerate(data, start=1):
        # Extract metadata
        product_name = entry.get("product_name", "Unknown Product")
        product_data = entry.get("product_data", [])

        for section_idx, section in enumerate(product_data, start=1):
            heading = section.get("heading", f"Section {section_idx}")
            content = section.get("data", {})
            title = content.get("Title", "No Title")
            body = content.get("Content", "No Content")

            # Add metadata
            metadata = {
                "product_name": product_name,
                "section_heading": heading,
                "section_title": title,
                "section_index": section_idx,
                "content": body
            }

            # Save each section as a separate JSON file
            output_file = Path(output_dir) / f"section_{idx}_{section_idx}.txt"
            with open(output_file, 'w', encoding='utf-8') as outfile:
                json.dump(metadata, outfile, indent=4, ensure_ascii=False)

            print(f"Saved: {output_file}")

# Example usage
input_json_file = 'Abilene-Texas.json'  # Replace with your input JSON file path
output_directory = 'split_sections'    # Replace with your desired output directory
split_json_and_add_metadata(input_json_file, output_directory)
