from argparse import ArgumentParser
import os
import pandas as pd
import glob
import json
from tqdm import tqdm
from multiprocessing import Pool


def remove_docstring(code, comment_list):
    assert type(code) == str
    
    # code_remove_comment = code.replace(docstring, '')
    for cmt in comment_list:
        code = code.replace(cmt, '')
        
    lines = [line for line in code.splitlines() if line.strip()]
    code = '\n'.join(lines)
        
    # for line in str(code).splitlines():
    #     include = False
    #     for cline in comment_list:
    #         if cline in line:
    #             include = True
    #     if not include:
    #         code_remove_comment += f'\n{line}'

    # code_remove_comment_line = sum([1 if line != '' else 0 \
    #     for line in str(code_remove_comment).splitlines()])
    
    return code


def load_data(args):
    print(args)
    file_path, save_path, idx = args
    name = os.path.basename(os.path.normpath(file_path))
    with open(save_path, 'a') as writer:
        with open(file_path, 'r') as infile:
            dataset = list(infile)
            for line in tqdm(dataset, position=idx, desc=f"Processing: {name}"):
                data = json.loads(line)
                
                original_code = data['code']
                cmts = data['comment']
                
                code = remove_docstring(original_code, cmts)
                data['code'] = code
                data['original_string'] = original_code
            
                json.dump(data, writer)
                writer.write('\n')
            

def parse_args():
    parser = ArgumentParser(description='merge dataset')
    parser.add_argument(
        "--data_path",
        type=str,
        help="path to raw dataset",
    )
    parser.add_argument(
        "--multiprocess",
        action='store_true',
        help="multiprocessing",
    )
    return parser.parse_args()


if __name__ == '__main__':
    opt = parse_args()
    listdir = os.listdir(opt.data_path)
    args = []
    
    for _dir in listdir:
        save_dir = os.path.join('/datadrive/dungnm31/data/full', _dir)
        os.makedirs(save_dir, exist_ok=True)
        file_list = glob.glob(os.path.join(opt.data_path, _dir, '*.jsonl'))
        idx = 0
        for file in file_list:
            name = os.path.basename(os.path.normpath(file))
            _save_dir = os.path.join(save_dir, name)
            args.append([file, _save_dir, idx])
            idx += 1
    
    if opt.multiprocess:
        with Pool(processes=20) as pool:
            # args = [(file, idx) for idx, file in enumerate(file_list)]
            pool.map(load_data, args)
    else:
        load_data(opt.data_path)
    