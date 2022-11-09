import argparse
import os
import json
import pathlib

import pandas as pd

from tqdm import tqdm

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', type=str, default='./cache')
    parser.add_argument('--max', type=int, default=20000)
    parser.add_argument('--ratio', type=float, default=0.05)

    return parser.parse_args()


if __name__ == '__main__':
    opt = args()
    max_sample, ratio, data_path = opt.max, opt.ratio, opt.data_path
    save_path = pathlib.Path(data_path).parent
    print(opt, save_path)
    
    
    with open(data_path, 'r') as json_file:
        dataset = list(json_file)
    
    valid_ratio = test_ratio = ratio
    ds_len = len(dataset)
    valid_len = min(max_sample, int(valid_ratio*ds_len))
    test_len = min(max_sample, int(test_ratio*ds_len))
    train_len = ds_len - valid_len - test_len
    
    print(f"Train size: {train_len} | Valid size: {valid_len} | Test ratio: {test_len}")

    infor_path = os.path.join(save_path, 'data_info.csv')
    if os.path.exists(infor_path):
        print("Found data_info.csv, start split dataset")
        df = pd.read_csv(infor_path)
        
    else:
        repos = []
        n_samples = []
        sets = []

        for i in tqdm(range(ds_len)):
            data = json.loads(dataset[i])
            repo = data['repo']
            
            # if repo not in df['repo'].values:
            if repo not in repos:
                # metadata = {'id': idx, 'repo': repo, 'path': path, 'n_sample': 1, 'set': None}
                # df2 = pd.DataFrame([metadata])
                # df = pd.concat([df, df2], ignore_index = True)
                
                # metadata = {'repo': repo, 'n_sample': 1, 'set': None}
                repos.append(repo)
                n_samples.append(1)
                sets.append(None)
                
            else:
                # df.loc[df['repo'] == repo, 'n_sample'] += 1
                index = repos.index(repo)
                n_samples[index] += 1
        
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

        df.to_csv(infor_path, index=False)

    trainfile = open(os.path.join(save_path, f'train.jsonl'), "a")
    validfile = open(os.path.join(save_path, f'valid.jsonl'), "a")
    testfile = open(os.path.join(save_path, f'test.jsonl'), "a")

    for ids in tqdm(range(len(dataset))):
        data = json.loads(dataset[ids])
        
        repo = data['repo']
        
        set_path = 'train'  # for new sample
        
        if repo in df['repo'].values:
            set_path = df.loc[df['repo'] == repo, 'set'].values[0]

        if set_path == 'train':
            json_object = json.dump(data, trainfile, ensure_ascii=False)
            trainfile.write('\n')
        elif set_path == 'test':
            json_object = json.dump(data, testfile, ensure_ascii=False)
            testfile.write('\n')
        elif set_path == 'valid':
            json_object = json.dump(data, validfile, ensure_ascii=False)
            validfile.write('\n')
