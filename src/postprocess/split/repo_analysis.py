import os
import glob
from tqdm import tqdm
from multiprocessing import Pool
from argparse import ArgumentParser

import hashlib
import json
import csv
import pandas as pd


def parse_args():
    parser = ArgumentParser(description='merge dataset')
    parser.add_argument(
        "--data_path",
        type=str,
        help="path to dir contains multiple raw dataset to merge",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        help="path to save merge file",
    )
    parser.add_argument(
        "--multiprocess",
        action='store_true',
        help="multiprocessing",
    )
    return parser.parse_args()


def repo_merge(args):
    data_path, save_path = args
    filename = os.path.basename(os.path.normpath(data_path))
    csv_output_filename = os.path.join(save_path, f'{filename}_repos.csv')
    
    # file_list = glob.glob(os.path.join(data_path, '*.csv'))

    df = pd.read_csv(data_path)
    grouped = df.groupby("Repo Name").mean()
    grouped.reset_index()
    grouped.to_csv(csv_output_filename, index=False)


if __name__ == '__main__':
    opt = parse_args()
    data_path = opt.data_path
    save_path = opt.save_path or opt.data_path
    file_list = glob.glob(os.path.join(data_path, '*.csv'))
    
    if opt.multiprocess:
        with Pool(processes=len(file_list)) as pool:
            args = [(file, save_path) for file in file_list]
            pool.map(repo_merge, args)
    else:
        for file in file_list:
            repo_merge(file)
