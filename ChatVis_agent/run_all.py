# ChatVis agent to run all test cases in the ChatVis benchmark

# import required modules

# --- Standard library ---
import os
import sys
import re
import json
import ast
import pickle
import subprocess
from pathlib import Path

# --- Third-party libraries ---
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import openai
import ollama

# --- Local utilities ---
from Utility.extract_utils import extract_python_code, extract_error_messages

# path to pvpython, replace with the actual path returned by `which pvpython`
path_to_pvpython = "/Applications/ParaView-5.13.2.app/Contents/Contents/bin:$PATH"  
os.environ["PATH"] += os.pathsep + path_to_pvpython

# OpenAI key, set through environment variable
API_KEY = os.getenv("API_KEY")
client = openai.OpenAI(
    api_key=API_KEY,
)

# Read and parse the JSON file
json_file_path = "operations.json"
with open(json_file_path, "r") as file:
    operations_json = json.load(file)

# Load a smaller Sentence Transformer model for efficiency
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Function to generate embeddings safely (one by one)
def get_embedding(text):
    return model.encode(text, convert_to_numpy=True).astype(np.float32)

# Initialize FAISS index
d = model.get_sentence_embedding_dimension()  # Get correct embedding dimension
index = faiss.IndexFlatL2(d)  # Use L2 distance metric for FAISS

# Generate and add embeddings for each operation
metadata_lookup = []
for op in operations_json:
    text = op["name"] + " " + op["description"] + " " + op["code_snippet"]
    embedding = get_embedding(text).reshape(1, -1)  # Reshape for FAISS
    index.add(embedding)
    metadata_lookup.append(op)  # Store the original entry

# Save the FAISS index to disk
faiss.write_index(index, "paraview_operations_faiss.index")

with open("metadata_lookup.pkl", "wb") as f:
    pickle.dump(metadata_lookup, f)
print("All ParaView operations stored in FAISS database.")

# search similar operations
def search_similar_operation(query_text, top_k=5):
    # Generate query embedding
    query_embedding = get_embedding(query_text).reshape(1, -1)

    # Ensure there are enough vectors in the FAISS index before searching
    total_vectors = index.ntotal
    if total_vectors == 0:
        print("Error: FAISS index is empty! No vectors found.")
        return []

    # Get nearest neighbors from FAISS
    top_k = min(top_k, total_vectors)  # Ensure we don't exceed available entries
    distances, indices = index.search(query_embedding, top_k)

    matches = []
    for idx in indices[0]:  # I is shape (1, k)
        match = metadata_lookup[idx]
        matches.append(match)

    return matches

# process prompt
def process_prompt(prompt: str):
    """
    Process a text prompt by splitting into lines, searching for similar operations,
    and returning unique operations by name.

    Args:
        prompt (str): The input prompt string.

    Returns:
        dict: A dictionary of unique operations keyed by name.
    """
    # Split prompt into non-empty lines
    prompt_lines = [line.strip() for line in prompt.strip().split('\n') if line.strip()]

    # Collect results
    all_results = []
    for line in prompt_lines:
        result = search_similar_operation(line)
        all_results.append(result)

    # Flatten list of lists
    flat_list = [item for sublist in all_results for item in sublist]

    # Deduplicate by name
    unique_ops = {}
    for op in flat_list:
        name = op['name']
        if name not in unique_ops:
            unique_ops[name] = op  # Keep the first occurrence

    return unique_ops

# system prompt
system_prompt =f'''You are a highly accurate code assistant specializing in 3D visualization scripting (e.g., ParaView, VTK). Your task is to read and execute the user's prompt line by line, ensuring that all operations, camera angles, views, rendering, and screenshots are handled correctly.

Execution Rules:
Process the Prompt Line-by-Line

Read and execute each instruction in order without skipping or merging steps.
If an operation depends on a previous step, ensure proper sequencing.
Camera and Viewing Directions

Object Creation and Rendering
Unless the user specifically instructs you to not show a data source, please show any data source after it has been loaded or created.

Apply background settings before rendering.
If a white background is needed for screenshots, ensure it is set before rendering.
Save screenshots immediately after rendering, before moving to the next step.
Ensure filenames or saving locations match the user’s intent.

Camera and Viewing Directions
If a specific camera direction or position is given by the user adjust the camera accordingly.
If the user does not specify how to zoom the camera, zoom the camera to fit the active rendered objects as the last operation in the script. Also, zoom the camera to fit the active rendered objects immediately before saving a screenshot. Call ResetCamera() on the render view object so that the camera will be zoomed to fit.
If the user manually specifies a camera zoom level, follow their instructions and do not insert extra calls to 'renderView.ResetCamera();layout = CreateLayout(name='Layout')layout.AssignView(0, renderView)'.

Use provided operation templates as references.
Maintain correct syntax, function calls, and parameters.
Code Quality & Best Practices

Ensure modular, readable, and structured code.
Add comments to explain significant steps.
Avoid redundant operations and ensure compatibility with visualization libraries.
Primary Goal:
Generate a precise, structured, and error-free script that accurately follows the user’s instructions, handling camera angles, views, rendering, and screenshots correctly. If any ambiguity exists, infer the most logical approach based on best practices. Follow Example Operations \n{operations_json}'''

# execute the agent on all the test cases

# model_name =  'AI4S-paper-prompt'#'gpt-4.5-preview'
python_file_name = '-full-prompt-2'

cwd = Path.cwd()
# eval_folder = str(cwd) + '/' + model_name + '/' #"/Users/oyildiz/Downloads/ChatVis/full-paper/eval/" + model_name + '/'
eval_folder = str(cwd) + '/' + "results" + '/'
os.makedirs(eval_folder, exist_ok=True)

folder_path = str(cwd.parent) + '/ChatVis_benchmark/test_cases/'

subfolders = [name for name in os.listdir(folder_path) 
              if os.path.isdir(os.path.join(folder_path, name))]

subfolder_paths = []
for folder in subfolders:
    subfolder_path = os.path.join(folder_path, folder)
    subfolder_paths.extend(
        os.path.join(subfolder_path, name) for name in os.listdir(subfolder_path) 
        if os.path.isdir(os.path.join(subfolder_path, name))
    )

# print("subfolder_paths", subfolder_paths)

# iterate thru all tasks
for folder in subfolder_paths:
    print("folder", folder)
    task = os.path.basename(folder)
    print("task", task)

    prompt_file = folder + "/full_prompt.txt"
    with open(prompt_file, "r") as file:
        prompt = file.read()
        print(prompt)

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        # model= "gpt-4o" #"gpt-4-turbo" #gpt-4o",
        model= "gpt5mini"
    )

    script = chat_completion.choices[0].message.content  
    
    file_path = extract_python_code(script, task+python_file_name)
    cfp = folder_path + task
    if file_path:
        
        # replace the pvpython path accordingly
        command = ["/Applications/ParaView-5.13.1.app/Contents/bin/pvpython", file_path] 

        result = subprocess.run(command, capture_output=True, text=True, cwd=cfp)
        print("Error message is: ", result.stderr)
        source_folder = cfp
        file_to_copy = task + "-screenshot.png"
        subprocess.run(["mv", os.path.join(source_folder, file_to_copy), eval_folder])

        errors = extract_error_messages(result.stderr)
        print(errors)

        attempts = 0
        while errors and attempts < 5:

            attempts = attempts + 1

            followup_question = f"""
            I tried running the following Python script and encountered an error.
            
            **Error Message:**
            {errors}
            
            **Original Script:**
            {script}
            
            Can you help me fix the issue and provide a corrected version of the script? 
            Please make sure the new script runs correctly without errors.
            """

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            
            messages.append({"role": "user", "content": followup_question})

            # Call the API again with full message history
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )
            
            # Assuming the AI provides new Python code in the response
            script = response.choices[0].message.content
            file_path = extract_python_code(script, task+python_file_name)
            
            # Execute the new script with pvpython
            command = ["/Applications/ParaView-5.13.2.app/Contents/bin/pvpython", file_path]
            result = subprocess.run(command, capture_output=True, text=True, cwd=cfp)

            # Extract errors from stderr, if any
            errors = extract_error_messages(result.stderr)
            if not errors:
                print("No more errors detected. Script executed successfully.")
                result = subprocess.run(command, capture_output=True, text=True, cwd=cfp)
                print("Error message is: ", result.stderr)
                source_folder = cfp
                file_to_copy = task + "-screenshot.png"
                subprocess.run(["mv", os.path.join(source_folder, file_to_copy), eval_folder])

                break
            else:
                print("Errors detected. Trying again...")

        subprocess.run(["mv", file_path, eval_folder])


