import os
import json
import argparse

import ast
from tqdm import tqdm

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default='./')
    return parser.parse_args()

opt = args()
data_path = opt.data_path

list_file = os.listdir(data_path)
if not list_file:
    raise ValueError(f'{data_path} is not a dir')

list_file = [file for file in list_file if 'batch' in file]
count, fail = 0, 0
with open(os.path.join(data_path, 'merged_function_data.jsonl'), 'a') as des_file:
    for file in tqdm(list_file):
        data = list(open(os.path.join(data_path, file), 'r'))
        # print(datas)
        # data = json.loads(file_reader)
        for item in data:
            try:
                item = json.loads(item)
            except Exception:
                fail += 1

            json.dump(item, des_file)
            count += 1
            des_file.write('\n')

print(f'Done, total sample {count}, fal {fail}')