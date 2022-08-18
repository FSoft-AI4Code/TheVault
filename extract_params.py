import re
import os
import json
import pathlib
import argparse
from typing import List

from tqdm import tqdm
from lizard import analyze_file


DOCSTRING_REGEX_TOKENIZER = re.compile(r"[^\s,'\"`.():\[\]=*;>{\}+-/\\]+|\\+|\.+|\(\)|{\}|\[\]|\(+|\)+|:+|\[+|\]+|{+|\}+|=+|\*+|;+|>+|\++|-+|/+")


def tokenize_docstring(docstring: str) -> List[str]:
    return [t for t in DOCSTRING_REGEX_TOKENIZER.findall(docstring) if t is not None and len(t) > 0]


def extract_function_params(function_code, comment, file_name,):
    metadata = {}
    report = analyze_file.analyze_source_code(file_name, function_code)
    # print(function_code)
    
    try:
        params = report.function_list[0].full_parameters  # 1 function only
    except IndexError:
        return None

    params_dict = {}
    
    # print(params)

    for each in params:
        line = str(each).split(' ')
        # print(line)
        params_dict[line[-1]] = {'docstring': False}
        
    preprocessed = re.split(r"(@+[\w]*)", comment)

    splited_comment = []
    line = ""
    for sub_str in preprocessed:
        if re.search(r"(@+[\w]*)", sub_str):
            splited_comment.append(line)
            line = re.search(r"(@+[\w]*)", sub_str).group()
        else: 
            line += sub_str
    splited_comment.append(line)
    # print(splited_comment)

    processed_docstring = []
    try:
        for line in splited_comment:
            if re.search(r"(@+[\w]*)", line):
                break_line = line.split(' ') # 0=tag, 1=type, 2=name
                if break_line[0] == '@param':
                    if break_line[2] not in params_dict.keys():
                        params_dict[break_line[2]] = {}
                    params_dict[break_line[2]]['type'] = re.search(r"\b\w*", break_line[1]).group()
                    params_dict[break_line[2]]['docstring'] = ' '.join(break_line[3:])

                else:
                    params_dict[break_line[0]] = ' '.join(break_line[1:])
            else:
                processed_docstring.append(line)
    except Exception:
        return None
    
    metadata['params'] = params_dict
    metadata['processed_docstring'] = processed_docstring
    metadata['processed_docstring_tokens'] = tokenize_docstring(' '.join(processed_docstring))
    # print(metadata)
    return metadata


def preprocessing_param(data_path):
    file_name = pathlib.PurePath(data_path).name
    save_dir = os.path.join(os.path.dirname(data_path), 'edited')
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)
    
    with open(data_path, 'r') as json_file:
        json_list = list(json_file)

    for json_str in tqdm(json_list):
        save_file = os.path.join(save_dir, f'edited_{file_name}')
        line = json.loads(json_str)  # each line is a function
        
        code = line['code']
        comment = line['docstring']
        path = pathlib.PurePath(line['path']).name
        
        metadata = extract_function_params(code, comment, path)
        if not metadata:
            save_file = os.path.join(save_dir, f'fail_{file_name}')  # and not update line
            
        else: 
            line.update(metadata)
            
        with open(os.path.join(save_file), "a") as outfile:
            json_object = json.dump(line, outfile)
            outfile.write('\n')
        
        # break
            

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='./CSN')

    return parser.parse_args()


if __name__ == "__main__":
    opt = args()
    data_path = opt.data  # './CSN'
    
    for language in ['python']: # ['ruby','go','java','php','python']:  # done java, javascript
        print(f"Preprocessing language: {language}")
        path = os.path.join(data_path, language)
        
        tags = [f'{x}.jsonl' for x in ['train', 'test', 'valid']]
        
        for tag in tags:
            preprocessing_param(data_path=os.path.join(path, tag))
    
    