import os
from typing import Dict
import json
import argparse
from tqdm import tqdm

from utils.languages_function import function_extract

def analysis_data(data_path, file_name):
    with open(data_path, 'r') as json_file:
        json_list = list(json_file)

    n_samples = len(json_list)  # data sample
    n_docstring = 0
    sum_string_len = 0
    sum_param = 0
    for json_str in tqdm(json_list):
        line = json.loads(json_str)  # each line is a function
        
        code = line['code']
        n_param = len(function_extract(code, 'abc.py'))
        n_docstring_token = len(line['processed_docstring_tokens'])
        params_docstring = line['docstring_params']
        
        docstring = False
        
        for param, value in params_docstring.items():
            if isinstance(value, Dict) and value:
                if value['docstring'] != None:
                    docstring = True
                
        if docstring:
            n_docstring += 1
        sum_param += n_param
        sum_string_len += n_docstring_token
        
    return {'name': file_name,
            '#data_sample': n_samples,
            '#with_docstring': n_docstring,
            'avg_param': sum_param/n_samples,
            'avg_doc_length': sum_string_len/n_samples}  # a dict


def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='./CSN/')

    return parser.parse_args()


if __name__ == "__main__":
    opt = args()
    data_path = opt.data  # './CSN'
    
    for language in ['python']: # ['ruby','go','java','php','python']:  # done java, javascript, ruby
        print(f"Preprocessing language: {language}")
        path = os.path.join(data_path, language, 'edited')
        
        tags = [f'edited_{x}.jsonl' for x in ['train', 'test', 'valid']]
        
        for tag in tags:
            print(f"Processing {tag} set")
            report = analysis_data(data_path=os.path.join(path, tag), file_name=tag)
            print(report)
