import os
import re
import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from assembly_parser import AssemblyParser
from c_parser import CParser

ALREADY_PROCESSED = set()
PROGRESS_FILE = "progress.txt"
FUNCT_NAME_PATTERN = r"\.def\s+([^;\s]+)"
NUM_WORKERS = 16
ASSEMBLY_DATASET = "../dataset_compiled_O0"
C_DATASET = "../dataset_clean"
FINAL_DATASET = "../dataset_tuples"

if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r") as fin:
        for line in fin:
            ALREADY_PROCESSED.add(line.strip())

def get_function_name_from_assembly(assembly_code: str) -> str:
    match = re.search(FUNCT_NAME_PATTERN, assembly_code)
    if match:
        return match.group(1)
    return None

def main(n: int, directory_path: str, lock):
    output_file = os.path.join(FINAL_DATASET, f"pairs_{n}.jsonl")
    all_dirs = sorted(os.listdir(directory_path))
    prog = 0
    for idx, dirname in enumerate(all_dirs):
        if idx % NUM_WORKERS != n or dirname in ALREADY_PROCESSED:
            continue 
        prog += 1
        if prog % 10 == 0:
            print(f"Worker {n}: Processing {dirname} ({prog}/{len(all_dirs)})")
        assembly_dir = os.path.join(directory_path, dirname)
        c_dir = os.path.join(C_DATASET, dirname)
        local_tuples = []
        for root, _, files in os.walk(assembly_dir):
            for file in files:
                if file.endswith(".o"):
                    c_source_file = os.path.join(c_dir, file[:-2] + ".c")
                    if not os.path.exists(c_source_file):
                        continue
                    try:
                        aParser = AssemblyParser(os.path.join(root, file))
                        cParser = CParser(c_source_file, anonymize=False)
                        aParser.parse()
                        cParser.parse()
                        data_segment, code_segments = aParser.get_elements()
                        functions = cParser.get_all_functions()
                        for func in code_segments:
                            func_name = get_function_name_from_assembly(func)
                            if func_name and func_name in functions:
                                local_tuples.append({
                                    "function_name": func_name,
                                    "assembly_code": func,
                                    "c_code": cParser.get_anon_function(func_name),
                                    "data_segment": data_segment
                                })
                    except Exception as e:
                        print(f"Error in {file}: {e}")
        if local_tuples:
            with open(output_file, "a", encoding="utf-8") as fout:
                for t in local_tuples:
                    fout.write(json.dumps(t) + "\n")
        with lock:
            with open(PROGRESS_FILE, "a") as f_prog:
                f_prog.write(f"{dirname}\n")

def init_pool(l):
    global lock
    lock = l

if __name__ == "__main__":
    if not os.path.exists(FINAL_DATASET):
        os.makedirs(FINAL_DATASET, exist_ok=True)
    with mp.Manager() as manager:
        shared_lock = manager.Lock()
        with ProcessPoolExecutor(max_workers=NUM_WORKERS, 
                                 initializer=init_pool,
                                 initargs=(shared_lock,)) as executor:
            executor.map(main, range(NUM_WORKERS), [ASSEMBLY_DATASET]*NUM_WORKERS, [shared_lock]*NUM_WORKERS)