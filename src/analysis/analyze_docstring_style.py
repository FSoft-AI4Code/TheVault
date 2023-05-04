import os
import json
import pandas as pd
import numpy as np
from collections import Counter
from tqdm import tqdm
import multiprocessing

def count_document_with_param(datafile):
    with open(datafile, 'r') as json_file:
        dataset = list(json_file)

    count = 0
    dis = []

    for dp in dataset:
        dp = json.loads(dp)
        
        att = 0
        for attr in dp['docstring_params']:
            if attr in ['returns', 'raises', 'others', 'outlier_params']:
                att += len(dp['docstring_params'][attr])
            elif attr == 'params':
                for param in dp['docstring_params'][attr]:
                    if param['docstring'] is not None and param['docstring'].strip() != "":
                        att += 1

        
        if att > 0:
            count += 1
            dis.append(att)
    return count, dis

clean_folder = "./clean/{}"
all_languages = ['python', 'php', 'javascript', 'java', 'c_sharp', 'c', 'cpp', 'ruby', 'rust']
dis = {lang: [] for lang in all_languages}

for lang in all_languages:
    print(lang)
    all_clean_files = [os.path.join(clean_folder.format(lang), filename) for filename in os.listdir(clean_folder.format(lang)) if "jsonl" in filename]
    cnt_raw_func = 0
    cnt_clean_func = 0

    pool = multiprocessing.Pool(processes=200)

    results = 0
    for result in tqdm(pool.map(count_document_with_param, \
                                    all_clean_files), \
                                    total=len(all_clean_files)):
        results += result[0]
        dis[lang] += result[1]
    print(results)

with open("./docattr.json", 'w') as f:
    json.dump(dis, f)

