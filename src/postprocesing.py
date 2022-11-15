import os
import json
import logging
import zipfile
import argparse
import subprocess
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.utils import create_logger


ROOT_PATH = str(Path(__file__).parents[1])

def seperate_filename(list_filename, parent_path):
    fn_list, cls_list, line_list = [], [], []
    for filename in list_filename:
        if 'function' in filename:
            fn_list.append(os.path.join(parent_path, filename))
        elif 'class' in filename:
            cls_list.append(os.path.join(parent_path, filename))
        elif 'line' in filename:
            line_list.append(os.path.join(parent_path, filename))
    
    if not line_list:
        return fn_list, cls_list

    return fn_list, cls_list, line_list


def check_file_size(list_file):
    valid_file = []
    for file in list_file:
        if os.path.getsize(file) > 0:
            valid_file.append(file)


def summary_total(list_file):
    for idx, lis in enumerate(list_file[:]):
        for file in lis[:]:
            if os.path.getsize(file) < 10:
                lis.remove(file)
                
    return list_file


def merge_embled_file(file_list, opt, name: str='raw_function', split: bool=False):
    """
    Count number of repo, number of sample
    Merge all .jsonl in file_list
    Split into train, test, set if flag split=True

    TODO: save into .zip file and run cloc
    """
    # For statistic
    fail_sample = 0
    n_sample = 0
    n_repos = set()
    
    # For analyzer
    repos = []
    n_samples = []
    sets = []
    zip_output = zipfile.ZipFile(os.path.join(opt.save_path, f'{name}_code.zip'), "w", zipfile.ZIP_DEFLATED)
    
    with open(os.path.join(opt.save_path, f'{name}_merge.jsonl'), 'a') as output_file:
        for file in tqdm(file_list, desc='Merging jsonl file'):
            with open(file, 'r') as json_file:
                dataset = list(json_file)
        
            for idx, data in enumerate(dataset):
                try:
                    data = json.loads(data)
                except Exception:
                    fail_sample += 1
                    continue
                
                assert 'code' in data.keys()
                assert 'repo' in data.keys()
                assert 'path' in data.keys()
                
                code = data['code']
                repo = data['repo']
                path = data['path']
                unique_idx = str(idx) + code[-10:] + repo + path[-50:]
                n_repos.add(repo)
                
                if repo not in repos:
                    repos.append(repo)
                    n_samples.append(1)
                    sets.append(None)
                
                else:
                    index = repos.index(repo)
                    n_samples[index] += 1
                
                if opt.analyze:
                    zip_output.writestr(unique_idx, code)
            
                json.dump(data, output_file)
                output_file.write('\n')
                n_sample += 1
                
    assert os.path.exists(os.path.join(opt.save_path, f'{name}_merge.jsonl')) == True
    assert os.path.exists(os.path.join(opt.save_path, f'{name}_code.zip')) == True
    logger.info('Meraged in %s' % (os.path.join(opt.save_path, f'{name}_merge.jsonl')))

    if opt.split and split:
        valid_ratio = test_ratio = opt.ratio
        valid_len = min(opt.max_sample, int(valid_ratio*n_sample))
        test_len = min(opt.max_sample, int(test_ratio*n_sample))
        train_len = n_sample - valid_len - test_len
        logger.info(f"Split data into: Train size: {train_len} ({(100*train_len/n_sample):.2f})% | Valid size: {valid_len} ({(100*valid_len/n_sample):.2f})% | Test ratio: {test_len} ({(100*test_len/n_sample):.2f})%")

        metadata_dict = {'repo': repos, 'n_sample': n_samples, 'set': sets}
        df = pd.DataFrame(metadata_dict, columns = ['repo', 'n_sample', 'set'])

        for index, row in tqdm(df.iterrows(), total=df.shape[0], desc='Spliting data'):
            if df.at[index, 'set'] is None:
                if valid_len - row['n_sample'] > 0:
                    valid_len -= row['n_sample']
                    df.at[index, 'set'] = 'valid'
                    
                elif test_len - row['n_sample'] > 0:
                    test_len -= row['n_sample']
                    df.at[index, 'set'] = 'test'
                
                else:
                    df.at[index, 'set'] = 'train'

        if not os.path.exists(os.path.join(opt.save_path, 'final')):
            os.mkdir(os.path.join(opt.save_path, 'final'))

        df.to_csv(os.path.join(opt.save_path, 'final', 'split_info.csv'), index=False)
            
        trainfile = open(os.path.join(opt.save_path, 'final', f'{name}_train.jsonl'), "a")
        validfile = open(os.path.join(opt.save_path, 'final', f'{name}_valid.jsonl'), "a")
        testfile = open(os.path.join(opt.save_path, 'final', f'{name}_test.jsonl'), "a")

        with open(os.path.join(opt.save_path, f'{name}_merge.jsonl'), 'r') as data_reader:
            dataset = list(data_reader)
        for ids in tqdm(range(len(dataset)), desc='Writing splited dataset'):
            data = json.loads(dataset[ids])
            
            repo = data['repo']
            
            set_path = 'train'  # for new sample
            
            if repo in df['repo'].values:
                set_path = df.loc[df['repo'] == repo, 'set'].values[0]

            if set_path == 'train':
                json.dump(data, trainfile, ensure_ascii=False)
                trainfile.write('\n')
            elif set_path == 'test':
                json.dump(data, testfile, ensure_ascii=False)
                testfile.write('\n')
            elif set_path == 'valid':
                json.dump(data, validfile, ensure_ascii=False)
                validfile.write('\n')
    

    # Analyze
    zip_output.close()
    if opt.analyze:
        command = f"cloc {os.path.join(opt.save_path, f'{name}_code.zip')} --processes={opt.n_core}"
        logger.info(f'============= Analyse source code in {name}_code.zip =============')
        command_line_process = subprocess.Popen(command,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.STDOUT,
                                                shell=True)
        process_output, _ = command_line_process.communicate()
        logger.info(process_output.decode())
    
    logger.info(f'============= SUMMARY: {name} | Total {n_sample} samples in {len(n_repos)} repos =============\n')


def merge_file(file_list, opt, name: str='raw', split: bool=False):
    if len(file_list) >= 2:  # function & class
        function_list, class_list = file_list[:2]
        
        merge_embled_file(function_list, opt, f'{name}_function', split)
        # merge_embled_file(class_list, opt, f'{name}_class', split)
        
        # if len(file_list) == 3:  # inline
        #     line_list = file_list[-1]
        #     merge_embled_file(line_list, opt, f'{name}_line', split=True)


def main(opt):
    assert os.path.exists(opt.data_path) == True, f"File or dir {opt.data_path} not found"
    if not os.path.exists(opt.save_path):
        os.mkdir(opt.save_path)
    
    raw_list_file = os.listdir(os.path.join(opt.data_path, 'raw'))
    filter_list_file = os.listdir(os.path.join(opt.data_path, 'filtered'))
    extract_list_file = os.listdir(os.path.join(opt.data_path, 'extracted'))
    
    raw_list = seperate_filename(raw_list_file, os.path.join(opt.data_path, 'raw'))
    filter_list = seperate_filename(filter_list_file, os.path.join(opt.data_path, 'filtered'))
    extract_list = seperate_filename(extract_list_file, os.path.join(opt.data_path, 'extracted'))
    
    
    raw_list = summary_total(raw_list)
    filter_list = summary_total(filter_list)
    extract_list = summary_total(extract_list)
    
    # s = f"RAW: #function file {len(raw_list[0])} | #class file {len(raw_list[1])} | #inline file {len(raw_list[2])}" + \
    # f"\nFILTERED: #function file {len(filter_list[0])} | #class file {len(filter_list[1])}" + \
    # f"\nEXTRACTED: #function file {len(extract_list[0])} | #class file {len(extract_list[1])}"
    # logger.info(s)
    
    merge_file(raw_list, opt, 'raw')
    merge_file(filter_list, opt, 'filter')
    merge_file(extract_list, opt, 'extract', split=True)
    logger.info('============= Done =============%')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'data_path', 
        help='data folder contain file.jsonl or huggingface dataset cache'
    )
    parser.add_argument(
        '--save_path', 
        type=str, 
        default='path/to/final',
        help='Save path'
    )
    parser.add_argument(
        '--n_core', 
        type=int, 
        default=0,
        help='Multiprocessing analyzer'
    )
    
    # Analyze
    parser.add_argument(
        '--analyze', 
        action='store_true',
        help=''
    )
    
    # Split into train/set/valid
    parser.add_argument(
        '--split', 
        action='store_true',
        help='Split data into train/set/valid or not'
    )
    parser.add_argument(
        '--ratio', 
        type=float, 
        default=0.05,
        help='test and valid ratio'
    )
    parser.add_argument(
        '--max_sample', 
        type=float, 
        default=20000,
        help='test and valid ratio'
    )

    opt = parser.parse_args()
    create_logger(filepath=os.path.join(opt.save_path, 'log.txt'), rank=0)
    
    logger = logging.getLogger()
    logger.info(f'Execute Arguments: {opt}')
    
    main(opt)
