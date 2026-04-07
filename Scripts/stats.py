import os

STAT_FILE = "stats.txt"
CLEANED_DIRECTORY = "../dataset_clean"
COMPILED_DIRECTORY = "../dataset_compiled_O0"

if __name__ == "__main__":
    total_files = 0
    successfully_compiled = 0
    for directory in os.listdir(CLEANED_DIRECTORY):
        input_directory = os.path.join(CLEANED_DIRECTORY, directory)
        output_directory = os.path.join(COMPILED_DIRECTORY, directory)
        for _,_, files in os.walk(input_directory):
            for file in files:
                if file[-1] == "c":
                    total_files +=1
                    if os.path.exists(os.path.join(output_directory, file[:-1]+"o")):
                        successfully_compiled += 1
    print(f"Total files: {total_files}")
    print(f"Successfully compiled: {successfully_compiled}")
    # with open(STAT_FILE, "w") as f:
    #     f.write(f"Total files: {total_files}\n")
    #     f.write(f"Successfully compiled: {successfully_compiled}\n")