import os
import argparse
import tempfile
from .preprocess import preprocess_binary, extract_assembly
from .ghidra_util import GhidraDecompiler
from .llm import decompile_using_gemini
import platform



if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Test the decompiler model on a sample assembly code.")
    arg_parser.add_argument("--input", type=str, help="Path to the input file.")
    arg_parser.add_argument("--output", type=str, help="Path to the output file.")
    arg_parser.add_argument("-t", choices = ["b","a"], help="type of the imput file\n\tb - binary, a - assembly.")
    arg_parser.add_argument("-m","--mode", choices = ["tbd", "llm", "ghidra"], default="tbd", help="mode of operation: tbd - use the decompiler model, llm - use gemini 2.5 flash, ghidra - use Ghidra's decompiler.")
    arg_parser.add_argument("--api", type=str, help="API key for the large language model (if mode is llm).")
    args = arg_parser.parse_args()
    input_path =  args.input
    if not os.path.exists(input_path):
        raise ValueError(f"The input path {input_path} doeas not exist")
    output_path = args.output
    file_type = args.t
    mode = args.mode
    api_key = args.api
    print("Executing tbd-cli with the following configuration")
    print(f"Input path{input_path}")
    print(f"Output path{output_path}")
    print(f"file_type {file_type}")
    print(f"mode {mode}")
    print(f"api key {api_key}")
    if api_key is None and mode == "llm":
        raise ValueError("API key is missing. When specifying the mode 'llm' you also have to specify an API key for it")
    assembly_functions = []
    data_segment = ""
    if file_type == "b":
        with tempfile.NamedTemporaryFile(mode = "w+t", encoding="utf-8", delete=True) as tmp:
            content = preprocess_binary(input_path)
            tmp.write(content)
            tmp.flush()
            data_segment, assembly_functions = extract_assembly(tmp.name)
    else:
        data_segment,assembly_functions = extract_assembly(input_path)
    c_functions = []
    if mode == "ghidra":
        gd = GhidraDecompiler()
        machine = platform.machine().lower()
        arch = "x86_64" if machine in ["x86_64", "arm64"] else "x86"
        c_functions = gd.decompile_assembly(assembly_functions=assembly_functions, arch=arch)
    elif mode == "llm":
        c_functions = decompile_using_gemini(api_key=api_key, assembly_functions=assembly_functions)
    else:
        from .trained_model import decompile_functions
        c_functions = decompile_functions(assembly_functions=assembly_functions, data_segment=data_segment)
    
    with open(output_path , "w") as fout:
        fout.write("\n\n".join(c_functions))