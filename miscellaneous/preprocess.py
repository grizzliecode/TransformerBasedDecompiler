import os
from typing import List, Tuple
import subprocess
from Scripts.assembly_parser import AssemblyParser


def preprocess_binary(input_file: str) -> None:
    command = ["objdump", "-d" , "-M", "intel", "--no-show-raw-insn", input_file]
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(f"Error during preprocessing: {e.decode()}")
    else:
        return o
    
def extract_assembly(input_file: str) -> Tuple[str, List[str]]: 
    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist.")
        raise FileNotFoundError(f"Input file {input_file} does not exist.")
    Aparser = AssemblyParser(input_file)
    Aparser.parse()
    return Aparser.get_elements()