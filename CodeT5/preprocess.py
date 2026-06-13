import json
from transformers import AutoTokenizer
from tqdm import tqdm

def preprocess_line_by_line(input_path, output_path, tokenizer, max_input_len=1024, max_output_len=512):
    size_margin = 20
    
    # Count lines dynamically for the progress bar without loading files into memory
    print(f"Scanning dataset size for {input_path}...")
    with open(input_path, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for _ in f)
        
    print(f"Processing {total_lines} rows sequentially (RAM footprint will remain near 0 MB)...")
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        for line in tqdm(f_in, total=total_lines, desc="Tokenizing"):
            try:
                item = json.loads(line)
            except Exception:
                continue
                
            assembly_code = item.get("assembly_code", "")
            c_code = item.get("c_code", "")
            context = item.get("data_segment", "")
            
            # Defensive character truncation: blocks rogue massive outlier files 
            # from blowing up the tokenizer's inner token-graph allocator.
            assembly_code = assembly_code[:30000]
            context = context[:30000]
            c_code = c_code[:30000]
            
            # Pre-calculate token lengths to decide prompt architecture
            assembly_enc = tokenizer.encode(assembly_code, add_special_tokens=False, truncation=True, max_length=max_input_len)
            context_enc = tokenizer.encode(context, add_special_tokens=False, truncation=True, max_length=max_input_len)
            
            if len(assembly_enc) + len(context_enc) <= max_input_len - size_margin:
                prompt = f"translate the following assembly to c: {context}\n{assembly_code}"
            else:
                prompt = f"translate the following assembly to c: {assembly_code}"
                
            # Convert final text to token arrays
            input_ids = tokenizer.encode(prompt, max_length=max_input_len, truncation=True)
            labels = tokenizer.encode(c_code, max_length=max_output_len, truncation=True)
            
            # Save token arrays directly to an output JSONL file
            tokenized_features = {
                "input_ids": input_ids,
                "labels": labels
            }
            f_out.write(json.dumps(tokenized_features) + "\n")

if __name__ == "__main__":
    model_name = "Salesforce/codet5p-770m"
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    print("\n--- Preprocessing Train Split ---")
    preprocess_line_by_line(
        "../dataset_commentless/train_original.jsonl", 
        "tokenized_train.jsonl", 
        tokenizer
    )
    
    print("\n--- Preprocessing Validation Split ---")
    preprocess_line_by_line(
        "../dataset_commentless/validation_original.jsonl", 
        "tokenized_validation.jsonl", 
        tokenizer
    )
    
    print("\nPreprocessing successfully finished! Ready for training.")