import os
import json
import csv
import glob
from tqdm import tqdm
import multiprocessing as mp
import pandas as pd
from argparse import ArgumentParser


def processing(data_path, _idx):
    language = os.path.basename(os.path.normpath(data_path))
    csv_files = ["medium_train.csv", "small_train.csv", "large_train.csv", "test.csv", "eval.csv"]
    sets = {"id": [], "set_name": []}
    # sets = []
    writer_list = {}
    for _csv in csv_files:
        path = os.path.join(data_path, f"{language}_{_csv}")
        set_name = _csv.replace('.csv', '')
        writer_list[set_name] = open(os.path.join(data_path, f"{set_name}.jsonl"), 'w')
        
        id_map = pd.read_csv(path)
        ids = id_map['ID']
        sets['id'].extend(ids)
        sets['set_name'].extend([set_name]*len(ids))
    
    writer_list['train'] = open(os.path.join(data_path, f"full_train.jsonl"), 'w')  # Must be write
    set_name_df = pd.DataFrame(sets, columns=['id', 'set_name'])
    
    # dataframe = {"id": [], "str_sample": []}
    dataframe = []
    with open(os.path.join(data_path, f'{language}_merged.jsonl'), 'r') as file:
        dataset = list(file)
        for data_point in tqdm(dataset, desc=f"Load {language} jsonl", total=len(dataset)):
            data_loaded = json.loads(data_point)
            dataframe.append([data_loaded['id'], data_point])
    content_df = pd.DataFrame(dataframe, columns=['id', 'str_sample'])
    content_df = content_df.drop_duplicates(subset='id', keep="first")

    result = pd.merge(set_name_df, content_df, on='id', how='outer')
    result['set_name'].fillna('train', inplace=True)
    # result.to_csv(os.path.join(data_path, 'split_meta.csv'))


    for index, row in tqdm(result.iterrows(), total=len(result), position=_idx, desc=language, leave=False):
        data_point = row['str_sample']
        set_name = row['set_name']
        writer_list[set_name].write(data_point)

        if set_name not in ['eval', 'test', 'train']:
            writer_list['train'].write(data_point)


def parse_args():
    parser = ArgumentParser(description='mapping dataset')
    parser.add_argument(
        "--data_path",
        type=str,
        help="path to raw dataset",
    )
    
    return parser.parse_args()


def main():
    opt = parse_args()
    languages = glob.glob(os.path.join(opt.data_path, '*'))
    print(languages)

    args = []
    for idx, _lang in enumerate(languages):
        # args.append((_lang, idx))
        processing(_lang, idx)
    
    # with mp.Pool(processes=10) as p:
    #     result = p.starmap(processing, args)
        


if __name__ == "__main__":
    main()
