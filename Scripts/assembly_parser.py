from enum import Enum
import os
import json


class SegmentationState(Enum):
    IDLE = 0
    DATA = 1
    CODE = 2



COMPILED_DATASET = "../dataset_compiled_O0"
CLEAN_DATASET = "../dataset_clean"
DATASET_PAIRS = "../dataset_pairs"

START_FUNCTION = {
    ".global",
    ".globl",
    ".def",
    ".type",
    ".cfi_startproc" 
}

END_FUNCTION = {
    # ".endef", 
    ".cfi_endproc",
    ".size",
    ".ident", 
    ".section",
    ".file"
}


DATA_START = {
    ".section\t.rodata",
    ".section\t.rdata",
    ".data",
    ".rodata",
    ".rdata",
    ".bss",
    ".section\t.data",
    ".section\t.bss"
}

DATA_END = {
    ".section\t.text",
    ".text",
    ".indent",
    ".file",
    ".def"
}


class AssemblyParser:
    def __init__(self, assembly_file: str):
        self.assembly_file = assembly_file
        self.data_segments = ""
        self.code_segments = []
        self.state = SegmentationState.IDLE

    def _get_signal_activations(self,line: str) -> tuple[int,int,int,int]:
        cs = any(map(lambda x: x in line, START_FUNCTION))
        ce = any(map(lambda x: x in line, END_FUNCTION))    
        ds = any(map(lambda x: x in line, DATA_START))
        de = any(map(lambda x: x in line, DATA_END))
        return cs, ce, ds, de

    def parse(self):
        current_data_segment = []
        current_code_segment = []
        if not os.path.exists(self.assembly_file):
            print(f"Assembly file {self.assembly_file} does not exist.")
            return
        with open(self.assembly_file, 'r') as fin:
            lines = fin.readlines()
            mx = len(lines)
            i = 0
            while i < mx:
                line = lines[i]
                cs, ce, ds, de = self._get_signal_activations(line)
                if self.state == SegmentationState.IDLE:
                    if cs and not ds:
                        self.state = SegmentationState.CODE
                        current_code_segment.append(line)
                        i+=1
                    elif ds and not cs:
                        self.state = SegmentationState.DATA
                        current_data_segment.append(line)
                        i+=1
                    else:
                        i+=1
                elif self.state == SegmentationState.DATA:
                    if not cs and de:
                        self.state = SegmentationState.IDLE
                    elif cs:
                        current_code_segment.append(line)
                        self.state = SegmentationState.CODE
                        i+=1
                    else:
                        current_data_segment.append(line)
                        i+=1
                elif self.state == SegmentationState.CODE:
                    if ce and not ds:  
                        self.state = SegmentationState.IDLE
                        self.code_segments.append("".join(current_code_segment))
                        current_code_segment = []
                    elif ds:
                        self.code_segments.append("".join(current_code_segment))
                        current_code_segment = []
                        current_data_segment.append(line)
                        self.state = SegmentationState.DATA
                        i+=1
                    else:
                        current_code_segment.append(line)
                        i+=1
            if len(current_code_segment) > 0:
                self.code_segments.append("".join(current_code_segment))
        self.data_segments = "\n".join(current_data_segment)
        

    def get_elements(self) -> tuple[list, str]:
        return self.data_segments, self.code_segments

   