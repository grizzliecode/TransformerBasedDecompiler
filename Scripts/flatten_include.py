import os
import re

INCLUDE_PATTERN = r'#include\s+(["<])(?:.*[\\/])?([^\\/">]+)([">])'
CLEANED_DIRECTORY = "../dataset_clean"


def flatten_include(file_name):
    with open(file_name, 'r') as f:
        content = f.read()

    content = re.sub(INCLUDE_PATTERN, r'#include \1\2\3', content)   

    with open(file_name, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    i = 0
    for directory in os.listdir(CLEANED_DIRECTORY):
        i+=1
        if i % 50 == 0:
            print(f"{i} projects processed")
        input_directory = os.path.join(CLEANED_DIRECTORY, directory)
        for root, _, files in os.walk(input_directory):
            for file in files:
                flatten_include(os.path.join(root, file))