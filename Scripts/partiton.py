import os
import random

INPUT_DIR = "../dataset_tuples"
OUTPUT_DIR = "../dataset"

def main():
    print("Partitioning the dataset into train, validation, and test")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    train_path = os.path.join(OUTPUT_DIR, "train_original.jsonl")
    test_path = os.path.join(OUTPUT_DIR, "test_original.jsonl")
    validation_path = os.path.join(OUTPUT_DIR, "validation_original.jsonl")
    with open(train_path, "w") as train_fin, open(test_path, "w") as test_fin, open(validation_path, "w") as validation_fin:
        for filename in os.listdir(INPUT_DIR):
            if filename.endswith(".jsonl"):
                with open(os.path.join(INPUT_DIR, filename), "r") as fin:
                    for line in fin:
                        rand_val = random.randint(0, 100)
                        if rand_val < 89:
                            train_fin.write(line)
                        elif rand_val < 90:
                            validation_fin.write(line)
                        else:
                            test_fin.write(line)

if __name__ == "__main__":
    main()