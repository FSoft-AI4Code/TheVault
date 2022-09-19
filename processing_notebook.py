# Databricks notebook source
import os
import json
import argparse
from tqdm import tqdm
import concurrent.futures
from tqdm import tqdm

from datasets import load_dataset
from tree_sitter import Parser, Language

from utils.languages_function import export_jsonl
from utils.parser.java_parser import JavaParser
from utils.parser.javascript_parser import JavascriptParser
from utils.parser.python_parser import PythonParser
from utils.tree_utils import import_language_parser, reformat_function_data

# COMMAND ----------

from pyspark.sql import SparkSession
appName = "PySpark open JSON line"
master = "local"
spark = SparkSession.builder \
    .appName(appName) \
    .master(master) \
    .getOrCreate()

account_name = "ai4codedatalake"
apikey = "W7G9tBs7aRVoce1sj2p8mAfYKniUaMUmHh3zs82H8EFA9pUyvBfMnlAc8LHET5vZD90v/FZar4od+AStZTNtfg=="

# session configuration
spark.conf.set(f"fs.azure.account.key.{account_name}.dfs.core.windows.net", apikey)

# COMMAND ----------

def export_jsonl(data, save_path):
    with open(os.path.join(save_path), "a") as outfile:
        json_object = json.dump(data, outfile)
        outfile.write('\n')
#     df = spark.createDataFrame(data)
#     df.write.format('json').mode('append').save(save_path)

# COMMAND ----------

def _processing(dataset, index, tree_dict, save_path, id=None):
#     pbar = tqdm(total=index, desc=f'Thread {id}', disable=False)
#     for _, ids in enumerate(index):
#         print(f'Thread {id}: [{_}/{len(index)}]')
    for ids in tqdm(index, desc=f'Thread {id}'):
        data = dataset[ids]
        
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

            if language == 'java':
                fn_metadata = list(JavaParser.get_definition(tree, raw_code))

            if language == 'javascript':
                fn_metadata = list(JavascriptParser.get_definition(tree, raw_code))

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

                outfile = open(os.path.join(save_path, 'function_data.jsonl'), "a")
                json_object = json.dump(item, outfile)
                outfile.write('\n')
            
        except Exception:
            file = open(os.path.join(save_path, 'fail.jsonl'), "a")
            json_object = json.dump(data, file)
            file.write('\n')
        
#         pbar.update(1)
    
#     save_file = os.path.join(save_path, 'function_data')
#     export_jsonl(processed_data, save_file)

# COMMAND ----------

def processing(dataset, save_path, n, split=96):
    # abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/javascript/small_data.jsonl
#     with open(data_path, 'r') as json_file:
#         dataset = list(json_file)
    
    dataset_size = len(dataset)
    index_list = range(dataset_size)
    print(save_path, split)
    chunk_size = dataset_size//split
    thread_jobs = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]
    
    tree_dict = import_language_parser()
    
    tmp_path = '/tmp/'
    dbutils.fs.rm('file:/tmp/function_data.jsonl', True)
    dbutils.fs.rm('file:/tmp/fail.jsonl', True)
    
#     for item in thread_jobs:
#         _processing(dataset, item, tree_dict, tmp_path)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = []
        for _, job in enumerate(thread_jobs):
            futures.append(executor.submit(_processing, dataset=dataset, index=job, tree_dict=tree_dict, save_path=tmp_path, id=_))

    for name in ['function_data.jsonl', 'fail.jsonl']:
        dbutils.fs.cp(f"file:{os.path.join(tmp_path,name)}", os.path.join(save_path, name), True)

# COMMAND ----------


