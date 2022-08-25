'''Parser code and extract params'''
import os
import re
import json
import argparse
import pathlib
from typing import List
from tqdm import tqdm
import concurrent.futures

from utils.tree_utils import extract_code_to_tree, import_language_parser
from utils.languages_function import export_jsonl, Java_extractor, Python_extractor


NUMBER_OF_FUNCTION = 0
NUMBER_OF_CLASS = 0


def extract_param(code, block_comment, path):
    path = pathlib.PurePath(path).name
    exactor = Python_extractor(code, block_comment, path)
    metadata = exactor.metadata
    return metadata


def processing(file, tree_dict, save_path, data_dir):
    print('Processing: ', file)
    f_counter, c_counter = 0, 0
    with open(os.path.join(data_dir, file), 'r') as json_file:
        json_list = list(json_file)
    
    for json_str in tqdm(json_list):
        line = json.loads(json_str)  # each line is 1 source code file

        func_list, class_list = extract_code_to_tree(line, tree_dict)
        func_save_path = os.path.join(save_path, 'function_data.jsonl')
        class_save_path = os.path.join(save_path, 'class_data.jsonl')
        
        # print(func_list, class_list)
        _processing(func_list, func_save_path)
        _processing(class_list, class_save_path)
        
    return

    
def _processing(data_list, save_path):
    for data in data_list:
        block_comment = data['docstring']['block_comment']
        if len(block_comment) >= 1:
            try:
                block_comment = block_comment[0]
                metadata = extract_param(data['code'], block_comment, data['path'])
            
                data.update(metadata)
                export_jsonl(data, os.path.join(save_path))
            except Exception:
                save_fail(data, save_path)
        
        else:
            save_fail(data, save_path)
            

def save_fail(data, save_path):
    with open(os.path.join(os.path.dirname(save_path), f'fail_sample.jsonl'), 'a') as file:
        json.dump(data, file)
        file.write('\n')


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--n_thread', type=int, default=10)
    parser.add_argument('--data_path', type=str, default='./data/python/raw/')
    parser.add_argument('--save_path', type=str, default='./data/python/')

    return parser.parse_args()


if __name__ == '__main__':
    opt = args()
    data_dir, n_thread, save_path = opt.data_path, opt.n_thread, opt.save_path
    
    tree_dict = import_language_parser()
    
    list_datafile = os.listdir(data_dir)
    # print(list_datafile)
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_thread) as executor:
        futures = []
        for idx, file in enumerate(list_datafile):
            futures.append(executor.submit(processing, file=file, tree_dict=tree_dict, 
                                           save_path=save_path, data_dir=data_dir,))
            
        for future in concurrent.futures.as_completed(futures):
            print(future.result())
            
    # print('Number of extracted function: ', f_counter)
    # print('Number of extracted class: ', c_counter)
    