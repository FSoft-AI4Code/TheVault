import os
import json
import logging
import zipfile
import argparse
import subprocess
from pathlib import Path

import pandas as pd
from tqdm import tqdm


logging.basicConfig(format = '%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt = '%m/%d/%Y %H:%M:%S',
                    level = logging.INFO)
logger = logging.getLogger('Post-processing')

ROOT_PATH = str(Path(__file__).parents[1])

def seperate_filname(list_filename, parent_path):
    fn_list, cls_list, line_list = [], [], []
    for filename in list_filename:
        if 'function' in filename:
            fn_list.append(os.path.join(parent_path, filename))
        if 'class' in filename:
            cls_list.append(os.path.join(parent_path, filename))
        else:
            line_list.append(os.path.join(parent_path, filename))

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

def merge_file(file_list, opt, s: str='RAW'):
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
    
    # For analyser
    repos = []
    n_samples = []
    sets = []
    zip_output = zipfile.ZipFile(f'{s}_code.zip', "w", zipfile.ZIP_DEFLATED)
    
    with open(opt.save_path, 'a') as output_file:
        for idx, file in enumerate(file_list):
            with open(file, 'r') as json_file:
                dataset = list(json_file)
        
            for data in dataset:
                try:
                    data = json.loads(data)
                except Exception:
                    fail_sample += 1
                    continue
                
                assert 'code' in data.keys
                assert 'repo' in data.keys
                assert 'path' in data.keys
                
                code = data['code']
                repo = data['repo']
                path = data['path']
                unique_path = idx + path[-50:]
                n_repos.add(repo)
                
                if repo not in repos:
                    repos.append(repo)
                    n_samples.append(1)
                    sets.append(None)
                
                else:
                    index = repos.index(repo)
                    n_samples[index] += 1
                
                if opt.analyse:
                    zip_output.writestr(unique_path, code)
            
                json.dump(data, output_file)
                output_file.write('\n')
                n_sample += 1

    if opt.split:
        valid_ratio = test_ratio = opt.ratio
        valid_len = min(opt.max_sample, int(valid_ratio*n_sample))
        test_len = min(opt.max_sample, int(test_ratio*n_sample))
        train_len = n_sample - valid_len - test_len

        metadata_dict = {'repo': repos, 'n_sample': n_samples, 'set': sets}
        df = pd.DataFrame(metadata_dict, columns = ['repo', 'n_sample', 'set'])

        for index, row in tqdm(df.iterrows(), total=df.shape[0]):
            if df.at[index, 'set'] is None:
                if valid_len - row['n_sample'] > 0:
                    valid_len -= row['n_sample']
                    df.at[index, 'set'] = 'valid'
                    
                elif test_len - row['n_sample'] > 0:
                    test_len -= row['n_sample']
                    df.at[index, 'set'] = 'test'
                
                else:
                    df.at[index, 'set'] = 'train'

        df.to_csv(os.path.join(opt.save_path, 'split_info'), index=False)

        trainfile = open(os.path.join(opt.save_path, f'train.jsonl'), "a")
        validfile = open(os.path.join(opt.save_path, f'valid.jsonl'), "a")
        testfile = open(os.path.join(opt.save_path, f'test.jsonl'), "a")

        for ids in tqdm(range(len(dataset))):
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
    
        logger.info(f"\n Split data into: Train size: {train_len} ({(train_len/n_sample):.2f})% | Valid size: {valid_len} ({(valid_len/n_sample):.2f})% | Test ratio: {test_len} ({(test_len/n_sample):.2f})%")

    # Analyze
    zip_output.close()
    if opt.analyse:
        command = f""
        subprocess.Popen(command ,shell=True).wait()
    
    logger.info('\n\n=============%s Total %i samples in %i repos =============%' % (name, n_sample, len(n_repos)))


def main(opt):
    assert os.path.exists(opt.data_path) == True, f"File or dir {opt.data_path} not found"
    if not os.path.exists(opt.save_path):
        os.mkdir(opt.save_path)
    
    raw_list_file = os.listdir(os.path.join(opt.data_path, 'raw'))
    filter_list_file = os.listdir(os.path.join(opt.data_path, 'filtered'))
    extract_list_file = os.listdir(os.path.join(opt.data_path, 'extracted'))
    
    raw_list = seperate_filname(raw_list_file, os.path.join(opt.data_path, 'raw'))
    filter_list = seperate_filname(filter_list_file, os.path.join(opt.data_path, 'filtered'))
    extract_list = seperate_filname(extract_list_file, os.path.join(opt.data_path, 'extracted'))
    
    raw_list = summary_total(raw_list)
    filter_list = summary_total(filter_list)
    extract_list = summary_total(extract_list)
    
    s = f"\nRAW | #function file {len(raw_list[0])} | #class file {len(raw_list[1])} | #inline file {len(raw_list[2])}" + \
    f"\nFILTERED | #function file {len(filter_list[0])} | #class file {len(filter_list[1])}" + \
    f"\nEXTRACTED | #function file {len(extract_list[0])} | #class file {len(extract_list[1])}"
    logger.info(s)

    # TODO Merge file


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
        '--n_test', 
        type=float, 
        default=0.05,
        help='test ratio'
    )
    parser.add_argument(
        '--n_valid', 
        type=float, 
        default=0.05,
        help='valid ratio'
    )

    opt = parser.parse_args()
    logger.info("")
    logger.info(f'Execute Arguments: {opt}')
    
    main(opt)
