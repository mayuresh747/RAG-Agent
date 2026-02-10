
import fitz  # PyMuPDF
import tiktoken
import os

# Sample files tailored to the user's specific directories
files = [
    "/Users/mayuri/Documents/Projects/RAG Agent/All Documents/IBC WA Docs/IBC International Building Code.pdf", # ~1.9MB
    "/Users/mayuri/Documents/Projects/RAG Agent/All Documents/Seattle_Active_DIR_Rules/17-2018 - Calculating Tree Valuations & Civil penalties for Tree Protection Code Violations.pdf", # ~800KB
    "/Users/mayuri/Documents/Projects/RAG Agent/All Documents/washington_court_opinions/State v. items.pdf" # Placeholder, I'll find a real one
]

# Let's actually list a few specific ones to be sure
real_files = [
    "/Users/mayuri/Documents/Projects/RAG Agent/All Documents/IBC WA Docs/IBC International Building Code.pdf",
    "/Users/mayuri/Documents/Projects/RAG Agent/All Documents/Seattle_Active_DIR_Rules/17-2017 - Stormwater Manual Vols.1-5.pdf", # Large 35MB
    "/Users/mayuri/Documents/Projects/RAG Agent/All Documents/washington_court_opinions/State v. Bell.pdf" # Small ~1MB
]

enc = tiktoken.get_encoding("cl100k_base")

print(f"{'File':<50} | {'Size (MB)':<10} | {'Tokens':<10} | {'Tokens/MB':<10}")
print("-" * 90)

total_tokens = 0
total_mb = 0

for file_path in real_files:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path} (not found)")
        continue
        
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
            
        tokens = len(enc.encode(text))
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        print(f"{os.path.basename(file_path)[:47]:<50} | {size_mb:<10.2f} | {tokens:<10} | {tokens/size_mb:<10.0f}")
        
        total_tokens += tokens
        total_mb += size_mb
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if total_mb > 0:
    avg_density = total_tokens / total_mb
    print("-" * 90)
    print(f"Average Tokens per MB: {avg_density:.0f}")
    
    # Total project size is ~2.6 GB = 2662 MB
    project_size_mb = 2662
    estimated_total_tokens = avg_density * project_size_mb
    print(f"Estimated Total Tokens for 2.6GB: {estimated_total_tokens:,.0f}")
