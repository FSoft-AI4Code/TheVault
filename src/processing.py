import os
import argparse
import time
import logging
import json
import yaml
from tqdm import tqdm
from pathlib import Path

import multiprocessing

from datasets import load_dataset
from tree_sitter import Parser, Language

from codetext.parser import *
from codetext.utils import build_language
from src.utils.logger import create_logger
from src.utils import extract_node, get_line_definitions,\
    get_node_definitions, process_raw_node, write_jsonl


ROOT_PATH = str(Path(__file__).parents[1])


def load_json(filepath):
    with open(filepath, 'r') as json_file:
        dataset = list(json_file)
    yield dataset


def main(opt):
    # Start processing
    start = time.perf_counter()
    if opt.n_core == -1:
        n_worker = multiprocessing.cpu_count()
    else: 
        n_worker = opt.n_core
        
    if opt.load_from_file:
        logger.info("============ Load dataset from file %s ... ============" % opt.data_path)
        if not str(opt.data_path).endswith(('json', 'jsonl')):
            raise ValueError("Not found `json` or `jsonl` file, instead found %s" % opt.data_path)
        
        with open(opt.data_path, 'r') as json_file:
            dataset = list(json_file)
            
    elif opt.cons_from_raw:
        logger.info("============ Load dataset from dir %s ... ============" % opt.data_path)
        assert os.path.exists(opt.data_path) and os.path.isdir(opt.data_path)
        dataset = [os.path.join(opt.data_path, item) for item in os.listdir(opt.data_path)]

    else:
        logger.info("============ Load dataset from HuggingFace %s ... ============" % opt.data_path)
        dataset = load_dataset("codeparrot/github-code", languages=[opt.language], split='train', cache_dir=opt.data_path)
    logger.info("Load dataset done. Number of sample: %i ============" % len(dataset))

    
    # start_executor(dataset, language, save_path, split, is_file)
    logger.info("============ Start multiprocessing using %i worker ============" % n_worker)
    
    # split dataset
    dataset_size = len(dataset)
    index_list = range(dataset_size)
    chunk_size = dataset_size//opt.n_split
    if opt.cons_from_raw:
        chunk_size = 1
    
    logger.info("Spliting %i samples into %i sub-dataset with chunk size %i" % (dataset_size, opt.n_split, chunk_size))
    
    jobs_list = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]  # n set
    args = []
    for idx, job_index in enumerate(jobs_list):
        args.append([dataset, job_index, opt, idx]) # opt.language, opt.save_path, idx, is_file])
    logger.info("Total %i processes" % len(args))
    
    if opt.debug:
    # # for debuging
        processing(dataset, jobs_list[0], opt)
    else:
        executor = multiprocessing.Pool(n_worker)
        # executor.starmap(processing, args)
        res = []
        for result in tqdm(executor.starmap(processing, args), total=len(args)):
            res.append(result)
    
    res = [sum(x) for x in zip(*res)]
    finish = time.perf_counter()
    logger.info("============ Processing done, finished in %.3f seconds ============" % (finish - start))
    logger.info("Level {}: Total Raw {} | Filterable {} | Extractable {} \n".format(opt.level, *res))


def processing(dataset, job_index, opt, idx=1): #language, save_path, idx=None, is_file=None):
    # setup language parser
    language = str(opt.language).lower()
    if language == "c++": language = "cpp"
    if language == "c#": language = "c_sharp"
    
    ast_parser = Parser()
    lang_path = os.path.join(ROOT_PATH, 'tree-sitter', f'{language}.so')
    if not os.path.exists(lang_path):
        logger.info("Language %s not found | Attempt to build it" % (opt.language))
        build_language(language)
        
    tree_language = Language(lang_path, language)
    ast_parser.set_language(tree_language)
    
    if language == 'c_sharp':
        language_parser = CsharpParser()
        
    elif language == 'c' or language == 'cpp':
        language_parser = CppParser()
        
    elif language == 'python':
        language_parser = PythonParser()

    elif language == 'java':
        language_parser = JavaParser()
    
    elif language == 'javascript':
        language_parser = JavascriptParser()
        
    elif language == 'go':
        language_parser = GoParser()
        
    elif language == 'ruby':
        language_parser = RubyParser()
        
    elif language == 'rust':
        language_parser = RustParser()

    elif language == 'php':
        language_parser = PhpParser()
        
    else:
        raise ValueError(f'Language {language} not supported')
    
    t_start = time.perf_counter()
    raw_path = os.path.join(opt.save_path, 'raw')
    filtered_path = os.path.join(opt.save_path, 'filtered')
    extracted_path = os.path.join(opt.save_path, 'extracted')
    
    for path in [raw_path, filtered_path, extracted_path]:
        os.makedirs(path, exist_ok = True)

    list_res = extracting(dataset, job_index, ast_parser, language_parser, idx, opt)
    
    t_finish = time.perf_counter()
    
    logger.info("Saved batch %i | Processing took %.3f s" % (idx, t_finish - t_start))
    
    return list_res


def extracting(dataset, indexs, ast, lang_parser, thread_idx, opt):    
    raw_set, filtered_set, extracted_set = [], [], []
    
    if opt.cons_from_raw:
        with open(dataset[indexs[0]], 'r') as file:
            dataset = list(file)
        indexs = range(len(dataset))
            
    for idx in tqdm(indexs, desc=f'Thread {thread_idx} processing: '):
        data = dataset[idx]
        if opt.load_from_file or opt.cons_from_raw:
            data = json.loads(data)
        assert os.path.exists(opt.data_format), "Not found data format (.yaml file)"
        
        with open(opt.data_format, 'r') as stream:
            data_format = yaml.safe_load(stream)
        
        # Load using format
        # Main content
        repo = data[data_format["repo"]]
        path = data[data_format["path"]]
        language = data[data_format["language"]]
        metadata_data = {"repo": repo, "path": path, "language": language}
        
        # Additional content
        for key in data_format.keys():
            if key not in ['code', 'repo', 'path', 'language']:
                metadata_data[key] = data[key]
        
        raw_code = data[data_format["code"]]
        tree = ast.parse(bytes(raw_code, "utf8"))

        # try:
        # Extract function
        if opt.cons_from_raw:
            raw_fn = [data]

        if opt.level == 'function':
            raw_fn = list(process_raw_node(tree, raw_code, lang_parser, metadata_data))
            filtered_fn_list = list(get_node_definitions(raw_fn))
            if str(language).lower() == 'go':
                extracted_function_list = filtered_fn_list
            else:
                extracted_function_list = list(extract_node(filtered_fn_list, language))
            
            raw_set.extend(raw_fn)
            filtered_set.extend(filtered_fn_list)
            extracted_set.extend(extracted_function_list)

        elif opt.level == 'class':
            if not str(language).lower() in ['go', 'c']:
                raw_class = list(process_raw_node(tree, raw_code, lang_parser, metadata_data, is_class=True))
                filtered_class_list = list(get_node_definitions(raw_class, raw_code))
                extracted_class_list = list(extract_node(filtered_class_list, language))
            
                raw_set.extend(raw_class)    
                filtered_set.extend(filtered_class_list)
                extracted_set.extend(extracted_class_list)
        
        elif opt.level == 'inline':
            raw_line = list(get_line_definitions(tree, raw_code, lang_parser, metadata_data))
            extracted_set.extend(raw_line)
        
    # Saving
    save_path = os.path.join(opt.save_path, opt.level)
    os.makedirs(save_path, exist_ok=True)
    raw_path = os.path.join(save_path, 'raw')
    filtered_path = os.path.join(save_path, 'filtered')
    extracted_path = os.path.join(save_path, 'extracted')
    
    write_jsonl(raw_set, os.path.join(raw_path, f'batch_{thread_idx}_{opt.level}.jsonl'))
    write_jsonl(filtered_set, os.path.join(filtered_path, f'batch_{thread_idx}_{opt.level}.jsonl'))
    write_jsonl(extracted_set, os.path.join(extracted_path, f'batch_{thread_idx}_{opt.level}.jsonl'))
    
    res = [len(raw_set), len(filtered_set), len(extracted_set)]
    msg = '====== End of batch {} ====== \n'.format(thread_idx) + \
        'Level {}: Total Raw {} | Filterable {} | Extractable {} \n'.format(opt.level, *res)
    
    logger.info(msg)
    return res


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'data_path', 
        help='data folder contain file.jsonl or huggingface dataset cache'
    )
    parser.add_argument(
        '--save_path', 
        type=str, 
        default='./data/',
        help='Processed data save path'
    )
    
    # Data settings
    parser.add_argument(
        '--level', 
        type=str, 
        default='function',
        help='Extract function/class/inline level or all'
    )
    parser.add_argument(
        '--language', 
        type=str, 
        default='Python',
        help='Declare processing language (e.g: Python, Java)'
    )
    parser.add_argument(
        '--data_format', 
        type=str,
        default="./data/format/codeparot-format.yaml",
        help='Path to file .yaml contains data format'
    )
    parser.add_argument(
        '--load_from_file', 
        action='store_true',
        help='Load from .json or .jsonl'
    )
    parser.add_argument(
        '--cons_from_raw', 
        action='store_true',
        help='Continues from raw .jsonl (pass folder path to data)'
    )
    parser.add_argument(
        '--raw_only', 
        action='store_true',
        help=''
    )
    parser.add_argument(
        '--filtered_only', 
        action='store_true',
        help=''
    )
    parser.add_argument(
        '--extracted_only', 
        action='store_true',
        help=''
    )
    
    # Processing on multiple CPUs
    parser.add_argument(
        '--n_split', 
        type=int, 
        default=40,
        help='Split all the raw data into N file and feed into process pool'
    )
    parser.add_argument(
        '--n_core',
        type=int,
        default=1,
        help='Number of maximum process to create'
    )
    parser.add_argument(
        '--debug',
        action='store_true'
    )

    opt = parser.parse_args()
    
    if not os.path.exists(opt.save_path):
        os.mkdir(opt.save_path)
    log_path = os.path.join(opt.save_path, 'log')
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    
    create_logger(filepath=os.path.join(log_path, 'log.txt'), rank=0)
    logger = logging.getLogger()
    logger.info(f'Execute Arguments: {opt}')
    multiprocessing.set_start_method("fork")
    main(opt)
