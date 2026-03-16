import os

DATA_RAW = "../dataset_raw"
DATA_CLEAN = "../dataset_clean"

EXTENSIONS = {"c", "h"}

def clean_directory(input_dir: str) -> list[str]:
    res = []
    if not os.path.exists(input_dir):
        return []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if len(file.split(".")) > 1 and file.split(".")[1] in EXTENSIONS:
                file_path = os.path.join(root, file)
                res.append((file_path, file)) 
    return res

if __name__ == "__main__":
    os.makedirs(DATA_CLEAN, exist_ok=True)
    i = 0
    for root in os.listdir(DATA_RAW):
        if i % 50 == 0:
            print(f"{i} projects processed")
        input_directory = os.path.join(DATA_RAW, root)
        files_to_coppy = clean_directory(input_dir=input_directory)
        if len(files_to_coppy) > 0:
            output_directory = os.path.join(DATA_CLEAN, root)
            for (file_path, file) in files_to_coppy:
                os.makedirs(output_directory, exist_ok=True)
                output_file = os.path.join(output_directory, file)
                with open(file_path, 'r', errors='ignore') as fin, open(output_file, 'w') as fout:
                    fout.write(fin.read())
        i+=1 