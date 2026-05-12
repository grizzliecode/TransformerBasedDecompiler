import torch
import os
import pandas as pd
from datasets import load_dataset
from transformers import (
    AutoTokenizer, 
    LongT5ForConditionalGeneration, 
    BitsAndBytesConfig,
    TrainingArguments, 
    Trainer, 
    DataCollatorForSeq2Seq,
    TrainerCallback
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, TaskType

MODEL_NAME = "google/long-t5-tglobal-large"
TRAIN_FILE = "../dataset/train.jsonl"
VALID_FILE = "../dataset/validation.jsonl"
OUTPUT_DIR = "./longt5-decompiler-output"
LOG_FILE = "training_loss_log.csv"

MAX_INPUT_LENGTH = 2048  
MAX_OUTPUT_LENGTH = 512
CONTEXT_THRESHOLD = 150

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
if tokenizer.pad_token is None:
    tokenizer.add_special_tokens({'pad_token': '[PAD]'})

def preprocess_function(examples):
    inputs = []
    for asm, ctx in zip(examples["assembly_code"], examples["data_segment"]):
        ctx_ids = tokenizer.encode(str(ctx), add_special_tokens=False)
        if 0 < len(ctx_ids) <= CONTEXT_THRESHOLD:
            inputs.append(f"translate assembly to c: {asm} context: {ctx}")
        else:
            inputs.append(f"translate assembly to c: {asm}")
    
    model_inputs = tokenizer(inputs, max_length=MAX_INPUT_LENGTH, truncation=True, padding="max_length")
    labels = tokenizer(text_target=examples["c_code"], max_length=MAX_OUTPUT_LENGTH, truncation=True, padding="max_length")
    
    labels_with_ignore_index = [
        [(label if label != tokenizer.pad_token_id else -100) for label in label_example]
        for label_example in labels["input_ids"]
    ]
    model_inputs["labels"] = labels_with_ignore_index
    return model_inputs

dataset = load_dataset("json", data_files={"train": TRAIN_FILE, "validation": VALID_FILE}, streaming=True)
tokenized_dataset = dataset.map(preprocess_function, batched=True, batch_size = 1000)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = LongT5ForConditionalGeneration.from_pretrained(
    MODEL_NAME, 
    quantization_config=bnb_config, 
    device_map="auto"
)
model.resize_token_embeddings(len(tokenizer))   

model = prepare_model_for_kbit_training(model)
lora_config = LoraConfig(
    r=16, lora_alpha=32, target_modules=["q", "v"], lora_dropout=0.05, task_type=TaskType.SEQ_2_SEQ_LM
)
model = get_peft_model(model, lora_config)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    eval_strategy="steps",
    eval_steps=200,
    learning_rate=5e-5,           # Lower LR = more stability
    warmup_steps=100,             # Ramps up the model slowly
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    weight_decay=0.01,
    max_steps=5000,
    per_device_eval_batch_size=4, 
    eval_accumulation_steps=10,
    # --- STABILITY SETTINGS ---
    bf16=True,                    # Use BFloat16 (Supported by RTX 5060)
    max_grad_norm=0.5,            # Hard cap on how much weights can change
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",     # High-efficiency optimizer
    logging_steps=5,
)

class LossLoggingCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            if "loss" in logs:
                log_df = pd.DataFrame([state.log_history[-1]])
                if not os.path.isfile(LOG_FILE):
                    log_df.to_csv(LOG_FILE, index=False)
                else:
                    log_df.to_csv(LOG_FILE, mode='a', header=False, index=False)

small_eval_dataset = tokenized_dataset["validation"].shuffle(seed=42, buffer_size=1000).take(100)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=small_eval_dataset,
    data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
    callbacks=[LossLoggingCallback()] 
)

if __name__ == "__main__":
    print(f"Starting training. Loss will be logged to {LOG_FILE}")
    trainer.train()
    model.save_pretrained("./final_decompiler_lora_adapter")
    history_df = pd.DataFrame(trainer.state.log_history)
    history_df.to_csv("full_training_history.csv", index=False)
    print("Training complete and logs saved.")