import os
import re
import subprocess
from multiprocessing import Pool


COMPILED_DIRECTORY = "../dataset_compiled_O0"
CLEANED_DIRECTORY = "../dataset_clean"
LOG_FILE = "log.txt"
STAT_FILE = "stats.txt"
MISSING_HEADER_PATTERN = r"[\s\S]*? No such file or directory[\s\S]*?#include [<\"](.*?)[>\"]"
MISSING_TYPE_PATTERN = r"unknown type name[\s\S]*? '(.*?)'"
MISSING_FUNCTION_PATTERN = r"implicit declaration of function '(.*?)'"

COMPILE_COMMAND = ["gcc", "-S", "-masm=intel", "-O0", "-fno-asynchronous-unwind-tables", "-I"]

MOCK_FILE = "mock.h"
MOCKED_CONTENT = ""

NUMBER_OF_WORKERS = 20
def load_mock():
    global MOCK_FILE, MOCKED_CONTENT
    with open(MOCK_FILE, 'r') as fin:
        MOCKED_CONTENT = fin.read()

def mock_header(header_file: str):
    with open(header_file, 'w') as fout:
        fout.write(MOCKED_CONTENT)

def solve_missing_headers(stderr: str, input_directory: str) -> bool:
    missing_headers = re.findall(MISSING_HEADER_PATTERN, stderr)
    if len(missing_headers) == 0:
        return False, ""
    else:
        for header in missing_headers:
            header_path = os.path.join(input_directory, header)
            if not os.path.exists(header_path):
                mock_header(header_path)
    return True, missing_headers[0]

def solve_missing_types(stderr: str, mocked_file_path:str) -> bool:
    missing_types = set(re.findall(MISSING_TYPE_PATTERN, stderr))
    if len(missing_types) == 0:
        return False
    else:
        with open(mocked_file_path, 'a') as fout:
            for missing_type in missing_types:
                fout.write(f"typedef int {missing_type};\n")
    return True

def solve_missing_functions(stderr: str, mocked_file_path:str) -> bool:
    missing_functions = set(re.findall(MISSING_FUNCTION_PATTERN, stderr))
    if len(missing_functions) == 0:
        return False
    else:
        with open(mocked_file_path, 'a') as fout:
            for missing_function in missing_functions:
                fout.write(f"extern int {missing_function}(...);\n")
    return True

def compile_c_code(input_file: str, output_file: str, input_directory: str, mock: bool = False) -> bool:
    new_command = [cmd for cmd in COMPILE_COMMAND]
    new_command.extend([input_directory, input_file, "-o", output_file])
    cst = 0
    mocked_file = ""
    while cst == 0:
        p = subprocess.Popen(new_command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        _, stderr = p.communicate()
        if mock:
            if p.returncode != 0:
                status, mocked_file = solve_missing_headers(stderr.decode(), input_directory)
                if not status:
                    if len(mocked_file) > 0:
                        mocked_file_path = os.path.join(input_directory, mocked_file)
                        status = solve_missing_types(stderr.decode(), mocked_file_path)
                        if not status:
                            status = solve_missing_functions(stderr.decode(), mocked_file_path)
                            if not status:
                                cst = 1
                    else:
                        cst = 1 
            else:
                cst = 2
        else:
            if p.returncode != 0:
                cst = 1 
            else:
                cst = 2  

    return cst == 2

def main(n: int, mock: bool = False):
    print(f"Worker {n} started")
    i = 0
    if not os.path.exists(COMPILED_DIRECTORY):
        os.makedirs(COMPILED_DIRECTORY)
    for directory in os.listdir(CLEANED_DIRECTORY)[n*100:(n+1)*100]:
        i+=1
        if i % 25 == 0:
            print(f"{i} projects processed")
        input_directory = os.path.join(CLEANED_DIRECTORY, directory)
        output_directory = os.path.join(COMPILED_DIRECTORY, directory)
        os.makedirs(output_directory, exist_ok=True)
        for _,_, files in os.walk(input_directory):
            for file in files:
                if file[-1] == "c":
                    compile_c_code(os.path.join(input_directory, file),
                                             os.path.join(output_directory, file[:-1]+"o"), input_directory, mock)
                    
if __name__ == "__main__":
    nums = [i for i in range(NUMBER_OF_WORKERS)]
    p = Pool(NUMBER_OF_WORKERS)
    with p:
        p.map(main, nums)
    for directory in os.listdir(COMPILED_DIRECTORY):
        potentially_empty = os.path.join(COMPILED_DIRECTORY, directory)
        if  len(os.listdir(potentially_empty)) == 0:
            os.rmdir(potentially_empty)

