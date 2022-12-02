import os
from typing import Dict
import json
import argparse
from tqdm import tqdm

from utils.languages_function import function_extract
from utils.tree_utils import tokenize_docstring

def analysis_data(data_path, file_name):
    with open(data_path, 'r') as json_file:
        json_list = list(json_file)

    n_samples = len(json_list)  # data sample
    n_docstring = 0
    sum_len_docstring = 0
    sum_comment_len = 0
    sum_param = 0
    
    for json_str in tqdm(json_list):
        line = json.loads(json_str)  # each line is a function
        
        code = line['code']
        name = line['path']
        try:
            n_param = len(function_extract(code, name))
        except Exception:
            n_param = 0
            
        n_docstring_token = len(line['docstring_tokens'])
        params_docstring = line['docstring_params']
        
        docstring = False
        len_docstring = 0
        n_param_have_docstring = 0
        
        for param, value in params_docstring.items():
            if isinstance(value, Dict) and value:
                if param == 'other_param':
                    continue 
                elif value['docstring'] != None:
                    docstring = True
                    n_param_have_docstring += 1
                    with open('./tmp.txt', 'a') as file:
                        file.write('\n' + value['docstring'])
                    len_docstring += len(tokenize_docstring(str(value['docstring'])))
                    
        if n_param_have_docstring != 0:
            len_docstring /= n_param_have_docstring
                
        if docstring:
            n_docstring += 1
            
        sum_len_docstring += len_docstring
        sum_param += n_param
        sum_comment_len += n_docstring_token
        
    return {'name': file_name,
            '#data_sample': n_samples,
            '#with_docstring': n_docstring,
            'avg_param': sum_param/n_samples,
            'avg_comment_len': sum_comment_len/n_samples,
            'avg_docstring_len': sum_len_docstring/n_samples}  # a dict


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default='./CSN/python.jsonl')

    return parser.parse_args()


if __name__ == "__main__":
    opt = args()
    data_path = opt.data_path  # './CSN'
    
    # for language in ['java']: # ['ruby','go','java','php','python']:  # done java, javascript, ruby
    #     print(f"Preprocessing language: {language}")
    #     path = os.path.join(data_path, language, 'edited')
        
    #     tags = [f'edited_{x}.jsonl' for x in ['train', 'test', 'valid']]
        
    #     for tag in tags:
    #         print(f"Processing {tag} set")
    #         report = analysis_data(data_path=os.path.join(path, tag), file_name=tag)
    
    report = analysis_data(data_path=os.path.join(data_path), file_name='train')
    print(report)
