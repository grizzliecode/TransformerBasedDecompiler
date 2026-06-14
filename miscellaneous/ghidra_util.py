import os 
import subprocess
import tempfile
import re
from typing import List
from pathlib import Path

class GhidraDecompiler:
    CURRENT_PATH = Path(__file__).resolve().parent
    JAVA_PATH = os.path.join(CURRENT_PATH, "DecompileScript.java")
    
    def __init__(self, ghidra_path: str = "/home/octa/ghidra_12.1.2_PUBLIC"):
        if not os.path.exists(ghidra_path):
            if not os.environ.get("GHIDRA_PATH"):
                raise FileNotFoundError(f"Ghidra path {ghidra_path} does not exist and GHIDRA_PATH environment variable is not set.")
            else:
                ghidra_path = os.environ.get("GHIDRA_PATH")
        self.headless_analyzer = os.path.join(ghidra_path, "support", "analyzeHeadless")
        if not os.path.exists(self.headless_analyzer):
            raise FileNotFoundError(f"Ghidra headless analyzer was not found at {self.headless_analyzer}")
        
    def load_jvscript(self) -> str:
        with open(self.JAVA_PATH, "r") as fin:
            text = fin.read()
        return text
    
    def decompile_assembly(self, assembly_functions: List[str], arch: str = "x86_64") -> List[str]:
        c_functions = []
        gcc_flag = "-m64" if arch == "x86_64" else "-m32"
        for assembly_code in assembly_functions:
            formatted_asm = f".intel_syntax noprefix\n.global ghidra_target\nghidra_target:\n{assembly_code}\n"
            with tempfile.TemporaryDirectory() as tmpdir:
                obj_file = os.path.join(tmpdir, "target.o")
                try:
                    subprocess.run(
                        ['gcc', gcc_flag, '-c', '-x', 'assembler', '-', '-o', obj_file],
                        input=formatted_asm,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    c_functions.append(f"/*Assembly Compilation Error:\n{e.stderr}*/")
                    continue                
                ghidra_script_path = os.path.join(tmpdir, "DecompileScript.java")
                with open(ghidra_script_path, "w") as f:
                    f.write(self.load_jvscript())
                cmd = [
                    "/home/octa/ghidra_12.1.2_PUBLIC/support/analyzeHeadless",
                    tmpdir, "TmpProject",
                    "-import", obj_file,
                    "-scriptPath", "/home/octa/licenta/TransformerBasedDecompiler/miscellaneous",  # Folder where the script lives
                    "-postScript", "DecompileScript.java",                                         # Name ONLY
                    "-deleteProject"
                ]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    c_functions.append(self._extract_c_code(result.stdout))
                except subprocess.CalledProcessError as e:
                    raise RuntimeError(f"Ghidra Execution Error:\n{e.stderr}\n{e.stdout}")
        return c_functions
        
    def _extract_c_code(self, stdout: str) -> str:
        lines = stdout.splitlines()
        extracted_lines = []
        in_block = False        
        for line in lines:
            if "===START_DECOMPILATION===" in line:
                in_block = True
                continue
            if "===END_DECOMPILATION===" in line:
                in_block = False
                break
            if in_block:
                cleaned = re.sub(r"INFO\s+DecompileScript\.java>\s*", "", line)
                cleaned = cleaned.replace(" (GhidraScript)", "").rstrip()
                extracted_lines.append(cleaned)
                
        if extracted_lines:
            return "\n".join(extracted_lines).strip()
        return "/*Failed to parse decompilation markers. Raw log:\n" + stdout + "*/"
    

if __name__ == "__main__":
    import sys
    asm_func_1 = """
    push    rbp
    mov     rbp, rsp
    mov     DWORD PTR [rbp-4], edi
    mov     DWORD PTR [rbp-8], esi
    mov     edx, DWORD PTR [rbp-4]
    mov     eax, DWORD PTR [rbp-8]
    add     eax, edx
    pop     rbp
    ret
    """
    asm_func_2 = """
    push    rbp
    mov     rbp, rsp
    mov     DWORD PTR [rbp-4], edi
    mov     DWORD PTR [rbp-8], esi
    mov     eax, DWORD PTR [rbp-4]
    cmp     eax, DWORD PTR [rbp-8]
    jge     .L2
    mov     eax, DWORD PTR [rbp-8]
    jmp     .L3
.L2:
    mov     eax, DWORD PTR [rbp-4]
.L3:
    pop     rbp
    ret
    """

    assembly_inputs = [asm_func_1, asm_func_2]
    print("[*] Initializing Ghidra Headless Decompiler...")
    try:
        decompiler = GhidraDecompiler(ghidra_path="/home/octa/ghidra_12.1.2_PUBLIC")
    except FileNotFoundError as err:
        print(f"[!] Initialization Failed: {err}")
        sys.exit(1)

    print(f"[*] Sent {len(assembly_inputs)} assembly functions to Ghidra. Processing...")
    print("[*] Note: This will take a few seconds per function due to JVM initialization overhead.")
    print("-" * 60)
    try:
        decompiled_outputs = decompiler.decompile_assembly(assembly_inputs, arch="x86_64")
    except FileNotFoundError:
        print(f"[!] Error: Could not find your Java script at '{GhidraDecompiler.JAVA_PATH}'.")
        print("    Ensure the file exists and is named 'DecompileScript.java'.")
        sys.exit(1)

    for idx, c_code in enumerate(decompiled_outputs, 1):
        print(f"\n--- Decompiled Output for Function #{idx} ---")
        print(c_code)
        print("-" * 60)