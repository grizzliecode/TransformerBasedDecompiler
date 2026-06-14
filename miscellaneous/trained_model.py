import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel
import os
from typing import List

BASE_MODEL = "Salesforce/codet5p-770m" 
LORA_ADAPTER_PATH = ""

MAX_INPUT_LENGTH = 1024
if not torch.cuda.is_available():
    raise RuntimeError("CUDA is not available! Check your NVIDIA drivers or PyTorch installation.")


def get_estimated_number_of_tokens(text: str, tokenizer):
    tokens = tokenizer.encode(text)
    return len(tokens)

def decompile(asm_code, data_segment, model, tokenizer):
    asm_len = get_estimated_number_of_tokens(asm_code, tokenizer=tokenizer)
    data_len = get_estimated_number_of_tokens(data_segment, tokenizer)
    MARGIN = 20
    if asm_len + data_len <= MAX_INPUT_LENGTH - MARGIN:
        prompt = f"translate the following assembly to c: {data_segment}{asm_code}"
    else:
        prompt = f"translate the following assembly to c: {asm_code}"
    inputs = tokenizer(
        prompt, 
        return_tensors="pt", 
        max_length=1024, 
        truncation=True
    )
    inputs = {k: v.to("cuda") for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model.generate(
            **inputs, 
            max_new_tokens=1024,       
            do_sample=True,      
            repetition_penalty=1.2,
            temperature = 0.2,
        )
    
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def decompile_functions(assembly_functions : List[str], data_segment: str) -> List[str]:
    if not os.environ.get("LORA_ADAPTER_CODET5P"):
        raise FileNotFoundError("The path to the lora adapter for the model was not specified in the LORA_ADAPTER_CODET5P")
    else:
        LORA_ADAPTER_PATH = os.environ.get("LORA_ADAPTER_CODET5P")
    c_functions = []
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True, model_max_length=MAX_INPUT_LENGTH)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        BASE_MODEL, 
        torch_dtype=torch.float32,
        device_map={"":"cuda"} 
    )
    try:
        model = PeftModel.from_pretrained(model, LORA_ADAPTER_PATH)
    except ValueError as e:
        raise ValueError(f"Got exception{e}\n Maybe the LORA_ADAPTER_CODET5P was not set or does not point to valid adapter file.")
    model.eval()
    for func in assembly_functions:
        try:
            c_func =  decompile(func, data_segment, model, tokenizer)
            c_functions.append(c_func)

        except Exception as e:
            c_functions.append(f"/*Exception when decompiling function {func}\n{e}*/")
    return c_functions