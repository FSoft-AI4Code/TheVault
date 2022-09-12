import re
import os
import json
import pathlib
import argparse
from typing import List

from tqdm import tqdm
from lizard import analyze_file

from utils.tree_utils import tokenize_docstring
from utils.languages_function import export_jsonl, Java_extractor, Python_extractor


def preprocessing_param(data_path):
    file_name = pathlib.PurePath(data_path).name
    save_dir = os.path.join(os.path.dirname(data_path), 'edited')
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    with open(data_path, 'r') as json_file:
        json_list = list(json_file)

    for json_str in tqdm(json_list):
        save_file = os.path.join(save_dir, f'edited_{file_name}')
        line = json.loads(json_str)  # each line is a function
        
        code = line['code']
        comment = line['docstring']
        path = pathlib.PurePath(line['path']).name
        
        exactor = Python_extractor(code, comment, path)
        metadata = exactor.metadata
        if not metadata:
            save_file = os.path.join(save_dir, f'fail_{file_name}')  # and not update line
            
        else: 
            line.update(metadata)
              
        export_jsonl(line, save_file)
            

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='./CSN/')

    return parser.parse_args()


if __name__ == "__main__":
    opt = args()
    data_path = opt.data  # './CSN'
    
    for language in ['python']: # ['ruby','go','java','php','python']:  # done java, javascript, ruby
        print(f"Preprocessing language: {language}")
        path = os.path.join(data_path, language)
        
        tags = [f'{x}.jsonl' for x in ['train', 'test', 'valid']]
        
        for tag in tags:
            print(f"Processing {tag} set")
            preprocessing_param(data_path=os.path.join(path, tag))
    
    