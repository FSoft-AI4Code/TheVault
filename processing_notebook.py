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

def export_jsonl(data, save_path):
    data.write.json.mode("append")\
            .option("header", True)\
            .option("quote", '"')\
            .option("escape", '"' "")\
            .save(save_path)

# COMMAND ----------

data = {"repo": "zship/deferreds.js", "path": "src/findSeries.js", "language": "JavaScript", "license": "mit", "func_name": "", "original_string": "function(list, iterator) {\n\n\t\tvar found;\n\n\t\treturn forEachSeries(list, function(item, i) {\n\t\t\treturn Promise.fromAny(iterator(item, i, list))\n\t\t\t\t.then(function(result) {\n\t\t\t\t\tif (result) {\n\t\t\t\t\t\tfound = item;\n\t\t\t\t\t\tthrow 'break';\n\t\t\t\t\t}\n\t\t\t\t});\n\t\t}).then(\n\t\t\tfunction() {\n\t\t\t\treturn found;\n\t\t\t},\n\t\t\tfunction(err) {\n\t\t\t\tif (err === 'break') {\n\t\t\t\t\treturn found;\n\t\t\t\t}\n\t\t\t\tthrow err;\n\t\t\t}\n\t\t);\n\n\t}", "code": "function(list, iterator) {\n\n\t\tvar found;\n\n\t\treturn forEachSeries(list, function(item, i) {\n\t\t\treturn Promise.fromAny(iterator(item, i, list))\n\t\t\t\t.then(function(result) {\n\t\t\t\t\tif (result) {\n\t\t\t\t\t\tfound = item;\n\t\t\t\t\t\tthrow 'break';\n\t\t\t\t\t}\n\t\t\t\t});\n\t\t}).then(\n\t\t\tfunction() {\n\t\t\t\treturn found;\n\t\t\t},\n\t\t\tfunction(err) {\n\t\t\t\tif (err === 'break') {\n\t\t\t\t\treturn found;\n\t\t\t\t}\n\t\t\t\tthrow err;\n\t\t\t}\n\t\t);\n\n\t}", "code_tokens": ["function", "(", "list", ",", "iterator", ")", "{", "var", "found", ";", "return", "forEachSeries", "(", "list", ",", "function", "(", "item", ",", "i", ")", "{", "return", "Promise", ".", "fromAny", "(", "iterator", "(", "item", ",", "i", ",", "list", ")", ")", ".", "then", "(", "function", "(", "result", ")", "{", "if", "(", "result", ")", "{", "found", "=", "item", ";", "throw", "'break'", ";", "}", "}", ")", ";", "}", ")", ".", "then", "(", "function", "(", ")", "{", "return", "found", ";", "}", ",", "function", "(", "err", ")", "{", "if", "(", "err", "===", "'break'", ")", "{", "return", "found", ";", "}", "throw", "err", ";", "}", ")", ";", "}"], "docstring": {"block_comment": "Version of find which is guaranteed to process items in order", "line_comment": None}, "docstring_tokens": ["Version", "of", "find", "which", "is", "guaranteed", "to", "process", "items", "in", "order"], "docstring_params": {"other_param": {"iterator": {"docstring": "", "type": "Function"}}, "list": {"docstring": "", "type": "Array"}, " iterator": {"docstring": None}, "return": {"docstring": "", "type": "Promise<Any>"}}}

# COMMAND ----------

from pyspark.sql import SparkSession
appName = "PySpark open JSON line"
master = "local"
spark = SparkSession.builder \
    .appName(appName) \
    .master(master) \
    .getOrCreate()

# COMMAND ----------

save_path = "abfss://ai4code@ai4codedatalake.dfs.core.windows.net//"
# data_reader = spark.read.json(json_file_path)
df = spark.createDataFrame([data])

# COMMAND ----------

display(df)

# COMMAND ----------

account_name = "ai4codedatalake"
apikey = "W7G9tBs7aRVoce1sj2p8mAfYKniUaMUmHh3zs82H8EFA9pUyvBfMnlAc8LHET5vZD90v/FZar4od+AStZTNtfg=="

# session configuration
spark.conf.set(f"fs.azure.account.key.{account_name}.dfs.core.windows.net", apikey)

# COMMAND ----------

df.write.json("abfss://ai4code@ai4codedatalake.dfs.core.windows.net/temp/file.json", mode="append")

# COMMAND ----------

data.write.json.mode("append")\
            .option("header", True)\
            .option("quote", '"')\
            .option("escape", '"' "")\
            .save(save_path)

# COMMAND ----------

export_jsonl(df, json_file_path)

# COMMAND ----------

def processing(_data, index, tree_dict, save_path, id=None):
    print(f'Thread {id}')
    for ids in tqdm(index):
        data = json.loads(_data[ids])
        
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
                
            import time
            start_time = time.time()
            if language == 'javascript':
                fn_metadata = list(JavascriptParser.get_definition(tree, raw_code))
            end_time = time.time()
            if end_time-start_time>10:
                print(f'Total time {(end_time-start_time):.2f} s')
            
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
                # export_jsonl(item, save_file)
                save_file = os.path.join(save_path, 'function_data.jsonl')
                export_jsonl(item, save_file)
#                 with open(os.path.join(save_path, 'function_data.jsonl'), "a") as outfile:
#                     json_object = json.dump(item, outfile)
#                     outfile.write('\n')
            
        except Exception:
            save_file = os.path.join(save_path, 'fail_sample.jsonl')
            export_jsonl(data, save_file)

# COMMAND ----------

def processing(dataset, save_path, n, split=10):
    # abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/javascript/small_data.jsonl
#     with open(data_path, 'r') as json_file:
#         dataset = list(json_file)
    
    dataset_size = len(dataset)
    index_list = range(dataset_size)
    chunk_size = dataset_size//split
    thread_jobs = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]
    
    tree_dict = import_language_parser()
    
    # for item in thread_jobs:
    #     processing(dataset, item, tree_dict, save_dir)
        
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = []
        for _, job in enumerate(thread_jobs):
            futures.append(executor.submit(processing, _data=dataset, index=job, tree_dict=tree_dict, save_path=save_path, id=_))

# COMMAND ----------

# if __name__ == '__main__':
#     opt = args()
#     n, spliter, save_dir, cache_path = opt.n_thread, opt.split, opt.save_path, opt.cache_path
#     dataset = load_dataset("codeparrot/github-code", languages=['Java'], split='train', cache_dir=cache_path)
    
#     if not os.path.exists(save_dir):
#         os.mkdir(save_dir)
#         os.mkdir(os.path.join(save_dir, 'cache'))
    
#     dataset_size = len(dataset)
#     index_list = range(dataset_size)
#     chunk_size = dataset_size//spliter
#     thread_jobs = [index_list[x:x+chunk_size] for x in range(0, dataset_size, chunk_size)]
    
#     tree_dict = import_language_parser()
    
#     with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
#         futures = []
#         for idx, job in enumerate(thread_jobs):
#             futures.append(executor.submit(processing, data=dataset, index=job, tree_dict=tree_dict, save_path=save_dir, idx=idx))

