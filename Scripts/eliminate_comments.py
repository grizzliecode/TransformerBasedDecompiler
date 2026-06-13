import json
import os
import re

PATTERN =  r'("(?:\\.|[^\\"])*")|(/\*.*?\*/)|(//.*?\n|//.*$)'

def replace(match):
        if match.group(1):
            return match.group(1)
        elif match.group(3):
            return "\n"
        return ""


def remove_c_comments(text):
    return re.sub(PATTERN, replace, text, flags=re.DOTALL | re.MULTILINE)

def remove_comments_from_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as fin,open(output_file, 'w', encoding='utf-8') as fout:
        for line in fin:
            if not line.strip():
                continue
            data = json.loads(line)
            if "c_code" in data:
                # print("old:\n",data["c_code"])
                data["c_code"] = remove_c_comments(data["c_code"])
                # print("new:\n",data["c_code"])
            fout.write(json.dumps(data) + '\n')
 

if __name__ == "__main__":
    if not os.path.exists("../dataset_commentless"):
        os.makedirs("../dataset_commentless")
    input_files = ["../dataset/train_original.jsonl", "../dataset/validation_original.jsonl", "../dataset/test_original.jsonl"]
    output_files = ["../dataset_commentless/train_original.jsonl", "../dataset_commentless/validation_original.jsonl", "../dataset_commentless/test_original.jsonl"]
    for input_file, output_file in zip(input_files, output_files):
        if not os.path.exists(input_file):
            print(f"Input file {input_file} does not exist. Skipping.")
            continue
        remove_comments_from_file(input_file, output_file)