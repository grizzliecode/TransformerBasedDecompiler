import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, TrainingArguments, Trainer, BitsAndBytesConfig, TrainerCallback, DataCollatorForSeq2Seq
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training, PeftModel
import os
import pandas as pd
import numpy
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

MAX_INPUT_LENGTH = 1024
SIZE_MARGIN = 20
MAX_OUTPUT_LENGTH = 512
model_name = "Salesforce/codet5p-770m"

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True,model_max_length=MAX_INPUT_LENGTH)

tokenized_dataset = load_dataset("json", data_files={
    "train": "tokenized_train.jsonl", 
    "validation": "tokenized_validation.jsonl"
})
OUTPUT_DIR = "./codet5p-lora-decompiler-output"

bnb_config = BitsAndBytesConfig(
    load_in_4bit = True,
    bnb_4bit_quant_type = 'nf4',
    bnb_4bit_compute_dtype = torch.bfloat16
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map={"": "cuda"},
    use_safetensors=False, 
)
model.config.n_positions = MAX_INPUT_LENGTH
model.config.max_position_embeddings = MAX_INPUT_LENGTH

lora_config = LoraConfig(
    r = 16,
    lora_alpha = 32,
    lora_dropout = 0.05,
    bias = "none",
    task_type = TaskType.SEQ_2_SEQ_LM,
    target_modules = ["q", "v", "k", "o"]
)

model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, lora_config)
data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    evaluation_strategy="steps",
    eval_steps = 250,
    eval_accumulation_steps=1,
    learning_rate=1e-5,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=5,
    lr_scheduler_type="cosine",
    weight_decay=0.01,
    max_steps=10000,
    per_device_eval_batch_size=4, 
    ignore_data_skip=True,
    greater_is_better=False,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    optim="adamw_8bit",
    logging_steps=5,
    prediction_loss_only=True,
)
small_eval_dataset = tokenized_dataset["validation"].shuffle(seed=42).select(range(500))
LOG_PATH = "./training_logs.txt"
if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, "w") as f:
        pass

class LossCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        with open(LOG_PATH, "a") as fin:
            if logs is not None and "loss" in logs:
                fin.write(f"Step {state.global_step}: loss = {logs['loss']}\n")
            elif logs is not None and "eval_loss" in logs:
                fin.write(f"Step {state.global_step}: eval_loss = {logs['eval_loss']}\n")

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=small_eval_dataset,
    callbacks=[LossCallback()],
    data_collator=data_collator,
)

if __name__ == "__main__":
    print(f"Starting training.")
    CHECKPOINT_PATH = "./codet5p-lora-decompiler-output/checkpoint-7000"
    trainer.train(resume_from_checkpoint=CHECKPOINT_PATH)
    model.save_pretrained("./final_decompiler_lora_adapter")
    history_df = pd.DataFrame(trainer.state.log_history)
    history_df.to_csv("full_training_history.csv", index=False)
    print("Training complete and logs saved.")