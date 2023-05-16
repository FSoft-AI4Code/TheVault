import os
import json
import csv
import glob
from tqdm import tqdm
import multiprocessing as mp
import pandas as pd


def index_mapping(iterator):
    sets, sample = iterator
    sample = json.loads(sample)
    for set_name, ids in sets.items():
        if sample["id"] in ids:
            return set_name, sample
    return 'train', sample


def index_mapping_iter(sample_iterator):
    with mp.Pool() as pool:
        for res in pool.imap_unordered(
            index_mapping,
            sample_iterator
        ):
            if res is not None:
                yield res


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
        # with open(path, 'r') as f:
        #     reader = csv.reader(f)
        #     ids = [row['ID'] for row in reader]
        #     print(ids)
        #     # sets.append([ids, set_name])
        #     sets['id'].extend(ids)
        #     sets['set_name'].extend([set_name]*len(ids))
            # sets[set_name] = ids
    writer_list['train'] = open(os.path.join(data_path, f"full_train.jsonl"), 'w')
    set_name_df = pd.DataFrame(sets, columns=['id', 'set_name'])
    
    # dataframe = {"id": [], "str_sample": []}
    dataframe = []
    with open(os.path.join(data_path, f'{language}_merged.jsonl'), 'r') as file:
        dataset = list(file)
        for data_point in tqdm(dataset, desc=f"Load {language} jsonl", total=len(dataset)):
            data_loaded = json.loads(data_point)
            dataframe.append([data_loaded['id'], data_point])
    content_df = pd.DataFrame(dataframe, columns=['id', 'str_sample'])
    print("Shape of set_name dataframe: ", len(set_name_df))
    print("Shape of content dataframe: ", len(content_df))

    print("Concating ...")
    result = pd.merge(set_name_df, content_df, on='id', how='outer')
    result['set_name'].fillna('train', inplace=True)
    # result.to_csv(os.path.join(data_path, 'split_meta.csv'))
    print("Done")

    for index, row in tqdm(result.iterrows(), total=len(result)): 
        data_point = row['str_sample']
        set_name = row['set_name']
        writer_list[set_name].write(data_point)
        # json.dump(data_point, writer_list[set_name])
        # writer_list[set_name].write('\n')
        if set_name not in ['eval', 'test', 'train']:
            # json.dump(data_point, writer_list['train'])
            writer_list['train'].write(data_point)
        
    
        # args = [(sets, item) for item in dataset]
        # for set_name, data_point in tqdm(index_mapping_iter(args), desc=data_path, total=len(dataset), position=_idx, leave=False):


def main():
    data_path = "/datadrive/dungnm31/data/ext5"
    languages = glob.glob(os.path.join(data_path, '*'))
    print(languages)

    for idx, _lang in enumerate(languages):
        processing(_lang, idx)


if __name__ == "__main__":
    main()
