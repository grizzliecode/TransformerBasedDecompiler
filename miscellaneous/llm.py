import os
import sys
from typing import List
from openai import OpenAI


def decompile_using_gemini(api_key: str, assembly_functions: List[str], model_name: str = "gemini-2.5-flash") -> List[str]:
    res = []
    if not api_key:
        raise ValueError("You need to specify an API key in order to use the LLM functionality.")
    client = OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=api_key
    )
    system_prompt = (
        "You are an expert reverse engineer and compiler engineer. "
        "Your task is to translate the provided assembly function into clean, syntactically correct C code. "
        "Respond ONLY with the raw C code block inside standard markdown triple backticks. Do not include any introductory or concluding explanations."
    )
    for assembly_code in assembly_functions:
        user_prompt = f"translate the following assembly function into c:\n{assembly_code}"
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
            raw_output = response.choices[0].message.content.strip()
            if raw_output.startswith("```c"):
                raw_output = raw_output.split("```c", 1)[1]
            elif raw_output.startswith("```"):
                raw_output = raw_output.split("```", 1)[1]
            if "```" in raw_output:
                raw_output = raw_output.split("```", 1)[0]
            res.append(raw_output.strip())
        except Exception as e:
            res.append(f"/* LLM API Error processing this block: {str(e)} */")
            
    return res

if __name__ == "__main__":
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        print("[!] Error: 'GEMINI_API_KEY' environment variable is missing.")
        print("[*] Please set it in your terminal before running:")
        print('    export GEMINI_API_KEY="your_actual_key_here"')
        sys.exit(1)

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

    print(f"[*] Initializing batch decompilation for {len(assembly_inputs)} functions...")
    print("[*] Dispatching requests to Gemini 2.5 Flash via OpenAI API layer...")
    print("-" * 65)

    decompiled_outputs = decompile_using_gemini(
        api_key=API_KEY, 
        assembly_functions=assembly_inputs,
        model_name="gemini-2.5-flash"
    )

    for idx, c_code in enumerate(decompiled_outputs, 1):
        print(f"\n[+] --- Gemini Decompiled Output for Function #{idx} ---")
        print(c_code)
        print("-" * 65)