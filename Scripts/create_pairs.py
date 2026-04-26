import os
import re
import json
from assembly_parser import AssemblyParser
        
def main(n: int):
    pass

if __name__ == "__main__":
    a = AssemblyParser("D:\\7th semester\\Licenta\\dataset_compiled_O0\\0xdea_semgrep-rules\\bad-words.o")
    a.parse()
    data_segments, code_segments = a.get_elements()
    with open("data_segments.json", "w") as fout:
        json.dump(data_segments, fout, indent=4)
    with open("code_segments.json", "w") as fout:
        json.dump(code_segments, fout, indent=4)