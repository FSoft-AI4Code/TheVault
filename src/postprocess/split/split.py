import os
import pandas as pd
import glob
import functools
from tqdm import tqdm
from multiprocessing import Pool
from argparse import ArgumentParser
from sklearn.model_selection import train_test_split


TEST_SIZE = 20000
SMALL_RATIO = 0.05
MEDIUM_RATIO = 0.25
LARGE_RATIO = 0.7

def train_test_stratified_sampling(dataframe_path, idx=0):
    dataframe = pd.read_csv(dataframe_path)
    test_size = TEST_SIZE
    
    data = dataframe.copy(deep=True)
    data = data.groupby(['Repo Name'])[['Code Length', 'Docs Length']].mean().reset_index()
    data['CL_bin'] = pd.qcut(data['Code Length'], 10, labels=False)

    # repo_ratio = len(dataframe) / len(data)
    # test_ratio = test_size / (len(data) * repo_ratio)
    test_ratio = SMALL_RATIO
    train_val_set, test_set, y_train_val, y_test = train_test_split(data, data[['CL_bin']], test_size=test_ratio, random_state=42, stratify=data[['CL_bin']])
    
    # eval_ratio = test_size / (len(train_val_set) * repo_ratio)
    eval_ratio = MEDIUM_RATIO * len(data) / len(train_val_set)
    train_set, eval_set = train_test_split(train_val_set, test_size=eval_ratio, random_state=42, stratify=y_train_val)

    train_set['Set Name'] = 'train'
    eval_set['Set Name'] = 'eval'
    test_set['Set Name'] = 'test'
    
    concat_df = pd.concat([train_set, eval_set, test_set], axis=0)
    concat_df = concat_df.drop(['CL_bin', 'Code Length', 'Docs Length'], axis=1)
    
    result_df = pd.merge(dataframe, concat_df, how='right', on='Repo Name')

    grouped = {}
    for name, group in result_df.groupby(['Set Name'])[['ID', 'Repo Name', 'Code Length', 'Docs Length']]:
        grouped[name] = group
        
    
    save_name = str(dataframe_path).replace('train.csv', '')
    # access the groups by their name
    grouped['train'].to_csv(f'{save_name}large_train.csv', index=False)
    grouped['eval'].to_csv(f'{save_name}medium_train.csv', index=False)
    grouped['test'].to_csv(f'{save_name}small_train.csv', index=False)
    
    # grouped['train'].to_csv(f'{save_name}train.csv', index=False)
    # grouped['eval'].to_csv(f'{save_name}eval.csv', index=False)
    # grouped['test'].to_csv(f'{save_name}test.csv', index=False)
    
    print(f"Done splitting {os.path.basename(os.path.normpath(dataframe_path))}")


def train_test_split_wrapper(args):
    dataframe_path, idx = args
    train_test_stratified_sampling(dataframe_path, idx)
    
    
def partition_sampling(dataframe, save_path):
    pass


def parse_args():
    parser = ArgumentParser(description='merge dataset')
    # parser.add_argument(
    #     "--metadata_path",
    #     type=str,
    #     help="path to metadata of the dataset (.csv)",
    # )
    parser.add_argument(
        "--data_path",
        type=str,
        help="path to raw dataset",
    )
    parser.add_argument(
        "--multiprocess",
        action='store_true',
        help="multiprocessing",
    )
    return parser.parse_args()


if __name__ == '__main__':
    opt = parse_args()
    data_path = opt.data_path
    file_list = glob.glob(os.path.join(data_path, '*train.csv'))
    
    if opt.multiprocess:
        with Pool(processes=len(file_list)) as pool:
            args = [(file, idx) for idx, file in enumerate(file_list)]
            pool.map(train_test_split_wrapper, args)
    else:
        for file in file_list:
            train_test_stratified_sampling(file)
    
    # data_path = "/datadrive/dungnm31/data-ai4code/hackathon/java_meta.csv"
    # df = pd.read_csv(data_path)
    # stratified_sampling(df, ['Code Length', 'Docs Length'])
    
    # csv_file = pd.read_csv("/datadrive/dungnm31/data-ai4code/hackathon/java_meta.csv")
    # save_path = "/datadrive/dungnm31/data-ai4code/"

    # stratified_sampling(csv_file, 1000, save_path)
