import torch
from transformers import AutoTokenizer, LongT5ForConditionalGeneration, BitsAndBytesConfig
from sacrebleu.metrics import BLEU
from codebleu import calc_codebleu
import json

MODEL_NAME = "google/long-t5-tglobal-large"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TEST_DATA_PATH = "../dataset/test.jsonl"
CONTEXT_THRESHOLD = 150  

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4", 
    bnb_4bit_compute_dtype=torch.bfloat16 
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = LongT5ForConditionalGeneration.from_pretrained(
    MODEL_NAME, 
    quantization_config=bnb_config,
    device_map="auto"
)

def eval_function(generated_code, reference_code):
    bleu = BLEU()
    bleu_score = bleu.sentence_score(generated_code, [reference_code]).score
    try:
        codebleu_score = calc_codebleu([[reference_code]], [generated_code], lang="c") 
        structure_score = codebleu_score["codebleu"] * 100
    except Exception as e:
        print(f"Error calculating CodeBLEU: {e}")
        structure_score = 0.0   
    return bleu_score, structure_score

def load_test_data():
    with open(TEST_DATA_PATH, "r") as fin:
        for line in fin:
            data = json.loads(line)
            yield data

def main(n: int=5, bounded: bool=True):
    for data in load_test_data():
        if bounded:
            n -= 1
            if n < 0:
                break
        assembly_code = data["assembly_code"]
        reference_code = data["c_code"]
        context = data["data_segment"]
        context_ids = tokenizer.encode(context, add_special_tokens=False)
        if len(context_ids) <= CONTEXT_THRESHOLD:
            input_text = f"translate assembly to c: {assembly_code} context: {context}"
        else:
            input_text = f"translate assembly to c: {assembly_code}"
        inputs = tokenizer(input_text, return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=512)
        prediction = tokenizer.decode(outputs[0], skip_special_tokens=True)
        bleu_score, structure_score = eval_function(prediction, reference_code)
        print(f"BLEU Score: {bleu_score:.2f}, CodeBLEU Score: {structure_score:.2f}")
        print(f"Generated Code:\n{prediction}\n")
        print(f"Reference Code:\n{reference_code}\n")

if __name__ == "__main__":
    main()