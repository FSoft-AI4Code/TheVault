import enum
import os
import json
import argparse
import time
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

import pandas as pd
from datasets import load_dataset
from tree_sitter import Parser, Language
from docstring_parser.common import ParseError

from utils.languages_function import export_jsonl
from utils.parser.go_parser import GoParser
from utils.parser.ruby_parser import RubyParser
from utils.parser.php_parser import PhpParser
from utils.parser.java_parser import JavaParser
from utils.parser.javascript_parser import JavascriptParser
from utils.parser.python_parser import PythonParser
from utils.tree_utils import import_language_parser, reformat_function_data


def args():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--data_file', type=str, default='./data/raw/python_data.jsonl')
    parser.add_argument('--language', type=str, default='Python')
    parser.add_argument('--save_path', type=str, default='./data/python/')
    parser.add_argument('--cache_path', type=str, default='./cache')
    parser.add_argument('-s', '--split', type=int, default=40)

    return parser.parse_args()


# def _processing(dataset, index, ast, lang_parser, idx=None):
def _processing(dataset, ast, lang_parser, idx=None):
    # for index in tqdm(index, desc=f'Thread {idx}'):
    for data in tqdm(dataset, desc=f'Thread {idx}'):
        data = json.loads(data)
        # data = dataset[ids]
        
        try:
            processed_data = {
                "repo": data["repo_name"],
                "path": data["path"],
                "language": data["language"],
                "license": data["license"],
            }
        except:
            raise ValueError('Mismatch key')
        
        raw_code = data["code"]
        tree = ast.parse(bytes(raw_code, "utf8"))
        
        try:
            fn_metadata = list(lang_parser.get_definition(tree, raw_code))
            
            fn_data = []
            if len(fn_metadata) > 0:
                fn_data = reformat_function_data(processed_data, fn_metadata)

            # We only take function which has docstring (block_comment) and
            # their docstring is larger than 3 words and smaller than 256 words
            for item in fn_data:
                if item['docstring']['block_comment'] == None:
                    continue
                if len(item['docstring_tokens']) <= 3 or len(item['docstring_tokens']) >= 256:
                    continue
                
                yield item
            
        except Exception: # (ParseError, AttributeError, TypeError, UnboundLocalError):
            # with open(os.path.join(os.path.dirname(save_path), f'{id}_fail.jsonl'), 'a') as file:
            #     json.dump(data, file)
            #     file.write('\n')
            pass
        

# def processing(dataset, index, language, save_path, idx=None):
def processing(dataset, language, save_path, idx=None):
    # setup language parser
    language = str(language).lower()
    if language == "c++": language = "cpp"
    if language == "c#": language = "c_sharp"
    
    ast_parser = Parser()
    tree_language = Language('./languages/my-languages.so', language)
    ast_parser.set_language(tree_language)
    
    if language == 'python':
        language_parser = PythonParser()

    elif language == 'java':
        language_parser = JavaParser()
    
    elif language == 'javascript':
        language_parser = JavascriptParser()
        
    elif language == 'go':
        language_parser = GoParser()
        
    elif language == 'ruby':
        language_parser = RubyParser()

    elif language == 'php':
        language_parser = PhpParser()
        
    else:
        raise ValueError(f'Language {language} not supported')
    # list_function = list(_processing(dataset, index, ast_parser, language_parser, idx))
    list_function = _processing(dataset, ast_parser, language_parser, idx)
    
    # df = pd.DataFrame.from_dict(list_function)
    # save_path = os.path.join(save_path, f'batch_{idx}_data.csv')
    # df.to_csv(save_path)
    
    n_sample = 0
    with open(os.path.join(save_path, f'batch_{idx}_data.jsonl'), "a") as outfile:
        for function in list_function:
            n_sample += 1
            json.dump(function, outfile, ensure_ascii=False)
            outfile.write('\n')
            
    return n_sample


def start_executor(dataset, language, save_path, n):
    """
    Multi-processing on CPUs
    
    :param dataset: huggingface dataset or list of json object
    :param language: language
    :param save_path: path to discrete save
    :param n: split dataset into n file. 
    """
    n_worker = multiprocessing.cpu_count()
    print(f'Using {n_worker} cores.')
    dataset_size = len(dataset)
    # index_list = range(dataset_size)
    chunk_size = dataset_size//n
    # jobs_list = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]  # n set
    jobs_list = [dataset[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]  # n set
    
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    
    # Start multiprocessing
    futures = []
    executor = ProcessPoolExecutor(max_workers=n_worker)
    for idx, jobs in enumerate(jobs_list):
        futures.append(executor.submit(processing,
            dataset=jobs,
            # index=job_index,
            language=language,
            save_path=save_path,
            idx=idx))
        
    total = 0
    for function in as_completed(futures):
        res = function.result()
        total += res
        print(f'Number of sample: {res}')
    
    print(f'\n========================\nTotal sample: {total}')
    
    # # for test 1 process
    # processing(dataset, language, save_path)
    
# if __name__ == '__main__':
#     opt = args()
#     n, language, spliter, save_dir, cache_path = opt.n_thread, opt.language, opt.split, opt.save_path, opt.cache_path
#     dataset = load_dataset("codeparrot/github-code", languages=[language], split='train', cache_dir=cache_path)
    
#     if not os.path.exists(save_dir):
#         os.mkdir(save_dir)
#         os.mkdir(os.path.join(save_dir, 'cache'))
    
#     # dataset_size = len(dataset)
#     dataset_size = 500000
#     index_list = range(dataset_size)
#     chunk_size = dataset_size//spliter
#     thread_jobs = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]
    
#     tree_dict = import_language_parser()
    
#     # for item in thread_jobs:
#     #     processing(dataset, item, tree_dict, save_dir)
    
#     with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
#         futures = []
#         for _, job in enumerate(thread_jobs):
#             futures.append(executor.submit(processing, dataset=dataset, index=job, tree_dict=tree_dict, save_path=save_dir, id=_))

if __name__ == '__main__':
    opt = args()
    n, language, save_path, cache_path = opt.split, opt.language, opt.save_path, opt.cache_path
    
    with open(cache_path, 'r') as json_file:
        dataset = list(json_file)
    
    # start = time.perf_counter()
    
    start_executor(dataset, language, save_path, n)
    
    # finish = time.perf_counter()
    # print('the program has finished in {} seconds'.format(finish - start))
