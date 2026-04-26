import os
import re
import json
from assembly_parser import AssemblyParser
from c_parser import CParser
        
def main(n: int):
    pass

if __name__ == "__main__":
    a = AssemblyParser("D:\\7th semester\\Licenta\\dataset_compiled_O0\\0xdea_semgrep-rules\\bad-words.o")
    a.parse()
    c = CParser("D:\\7th semester\\Licenta\\dataset_clean\\0xdea_semgrep-rules\\bad-words.c")
    c.parse()
    data_segments, code_segments = a.get_elements()
    functions = c.get_all_functions()
    ast = c.get_all_asts()
    with open("data_segments.json", "w") as fout:
        json.dump(data_segments, fout, indent=4)
    with open("code_segments.json", "w") as fout:
        json.dump(code_segments, fout, indent=4)
    with open("functions.json", "w") as fout:
        json.dump(functions, fout, indent=4)
    with open("asts.json", "w") as fout:
        json.dump(ast, fout, indent=4)