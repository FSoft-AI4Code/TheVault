import os
import json
import argparse
from tqdm import tqdm
import concurrent.futures
from tqdm import tqdm

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
    parser.add_argument('-n', '--n_thread', type=int, default=10)
    parser.add_argument('-s', '--split', type=int, default=40)

    return parser.parse_args()


def processing(dataset, index, tree_dict, save_path, id=None):
    if not os.path.exists(save_path):
        os.mkdir(save_path)

    for ids in tqdm(index, desc=f'Thread {id}'):
        data = json.loads(dataset[ids])
        # data = dataset[ids]
        
        try:
            processed_data = {
                "repo": data["repo_name"],
                "path": data["path"],
                "language": data["language"],
                "license": data["license"],
                # "size": data["size"]
            }
        except:
            raise ValueError('Mismatch key')
        
        # get language
        language = str(data["language"]).lower()
        if language == "c++": language = "cpp"
        if language == "c#": language = "c_sharp"
        
        
        parser = Parser()
        parser.set_language(tree_dict[str(language).lower()])
        
        # tree parser
        raw_code = data["code"]
        tree = parser.parse(bytes(raw_code, "utf8"))
        root_tree = tree.root_node
        
        try:
            if language == 'python':
                function_list = list(PythonParser.get_function_definitions(root_tree))
                fn_metadata = list(PythonParser.process_functions(function_list, raw_code))

            elif language == 'java':
                fn_metadata = list(JavaParser.get_definition(tree, raw_code))
            
            elif language == 'javascript':
                fn_metadata = list(JavascriptParser.get_definition(tree, raw_code))
                
            elif language == 'go':
                fn_metadata = list(GoParser.get_definition(tree, raw_code))
                
            elif language == 'ruby':
                fn_metadata = list(RubyParser.get_definition(tree, raw_code))

            elif language == 'php':
                fn_metadata = list(PhpParser.get_definition(tree, raw_code))
            
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
                # export_jsonl(item, save_file)
                with open(os.path.join(save_path, f'batch_{id}_data.jsonl'), "a") as outfile:
                    json_object = json.dump(item, outfile, ensure_ascii=False)
                    outfile.write('\n')
            
        except (ParseError, AttributeError, TypeError):
            with open(os.path.join(os.path.dirname(save_path), f'{id}_fail.jsonl'), 'a') as file:
                json.dump(data, file)
                file.write('\n')
        


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
    n, spliter, save_dir, cache_path = opt.n_thread, opt.split, opt.save_path, opt.cache_path
    with open(cache_path, 'r') as json_file:
        dataset = list(json_file)
    
    # if not os.path.exists(save_dir):
    #     os.mkdir(save_dir)
    #     os.mkdir(os.path.join(save_dir, 'cache'))
    
    dataset_size = len(dataset)
    index_list = range(dataset_size)
    chunk_size = dataset_size//spliter
    thread_jobs = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]
    
    tree_dict = import_language_parser()
    
    for item in thread_jobs:
        processing(dataset, item, tree_dict, save_dir)
    
    # with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
    #     futures = []
    #     for _, job in enumerate(thread_jobs):
    #         futures.append(executor.submit(processing, dataset=dataset, index=job, tree_dict=tree_dict, save_path=save_dir, id=_))
