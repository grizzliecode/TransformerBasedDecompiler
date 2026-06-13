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
        if 0 < len(ctx_ids) and  len(ctx_ids) <= CONTEXT_THRESHOLD:
            inputs.append(f"translate the following assembly to c: {ctx}\n{asm}")
        else:
            inputs.append(f"translate the following assembly to c: {asm}")
    model_inputs = tokenizer(inputs, max_length=MAX_INPUT_LENGTH,padding = "max_length", truncation=True)
    labels = tokenizer(text_target=examples["c_code"], max_length=MAX_OUTPUT_LENGTH, padding="max_length", truncation=True)
    labels_with_ignore_index = []
    for label_example in labels["input_ids"]:
        labels_with_ignore_index.append(
            [label if label != tokenizer.pad_token_id else -100 for label in label_example]
        )
        
    model_inputs["labels"] = labels_with_ignore_index
    return model_inputs

dataset = load_dataset("json", data_files={"train": TRAIN_FILE, "validation": VALID_FILE}, streaming=True)
tokenized_dataset = dataset.map(preprocess_function, batched=True, batch_size=1000)

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
model = prepare_model_for_kbit_training(model)
model.resize_token_embeddings(len(tokenizer))
lora_config = LoraConfig(
    r=16, lora_alpha=32, target_modules=["q", "v", "k", "o", "wi", "wo"], lora_dropout=0.05, task_type=TaskType.SEQ_2_SEQ_LM
)
model = get_peft_model(model, lora_config)
model.set_input_embeddings(model.get_input_embeddings())

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    eval_strategy="steps",
    eval_steps=250,
    learning_rate=7e-5,
    warmup_steps=200,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=5,
    lr_scheduler_type="cosine",
    weight_decay=0.005,
    max_steps=10000,
    per_device_eval_batch_size=4, 
    eval_accumulation_steps=10,
    ignore_data_skip=True,
    greater_is_better=False,
    bf16=True,
    max_grad_norm=1.0,
    gradient_checkpointing=True,
    optim="paged_adamw_8bit",
    logging_steps=5,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
)

class LossLoggingCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            log_entry = {
                "step": state.global_step,
                "learning_rate": logs.get("learning_rate", None),
                "loss": logs.get("loss", None),
                "eval_loss": logs.get("eval_loss", None)
            }
            if log_entry["loss"] is not None or log_entry["eval_loss"] is not None:
                log_df = pd.DataFrame([log_entry])
                if not os.path.isfile(LOG_FILE):
                    log_df.to_csv(LOG_FILE, index=False)
                else:
                    log_df.to_csv(LOG_FILE, mode='a', header=False, index=False)

small_eval_dataset = tokenized_dataset["validation"].shuffle(seed=42, buffer_size=2000).take(1000)
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model
)
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=small_eval_dataset,
    data_collator=data_collator,
    callbacks=[LossLoggingCallback()] 
)

if __name__ == "__main__":
    print(f"Starting training. Loss will be logged to {LOG_FILE}")
    CHECKPOINT_PATH = os.path.join(OUTPUT_DIR, "checkpoint-4000")
    trainer.train(resume_from_checkpoint=CHECKPOINT_PATH if os.path.exists(CHECKPOINT_PATH) else None)
    model.save_pretrained("./final_decompiler_lora_adapter")
    history_df = pd.DataFrame(trainer.state.log_history)
    history_df.to_csv("full_training_history.csv", index=False)
    print("Training complete and logs saved.")
