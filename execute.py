# Databricks notebook source
# MAGIC %md # Test

# COMMAND ----------

from docstring_parser import parse, DocstringStyle

# COMMAND ----------

text = """
    This is a function.

    @param {string[]} n
    @param {string[]} n - A string param
    @param n {string[]} - A string param
    @typedef {Object} Song
    @type {Object} Song
    @param {string} [o] - A optional string param
    @param {string} [d=DefaultValue] - A optional string param
    @return {string} A good string
    @return {string}
    @property {string} title - The title
    @property {string} artist - The artist
    @property {number} year - The year
    @throws {FooException}
    @example
        foo('hello')
"""

# COMMAND ----------

ret = parse(text, DocstringStyle.JSDOC)
print('short', ret.short_description)
print('long', ret.long_description)
print(ret.style)
# print(ret.__dict__)
for a in ret.meta:
    print(a.__dict__)

# COMMAND ----------

# MAGIC %md # Execution

# COMMAND ----------

account_name = "ai4codedatalake"
apikey = "W7G9tBs7aRVoce1sj2p8mAfYKniUaMUmHh3zs82H8EFA9pUyvBfMnlAc8LHET5vZD90v/FZar4od+AStZTNtfg=="

# session configuration
spark.conf.set(f"fs.azure.account.key.{account_name}.dfs.core.windows.net", apikey)

# COMMAND ----------

container_name = "ai4code"
folder_name = "small_dataset"
blob_names = dbutils.fs.ls(f"abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/")
display(blob_names)

# COMMAND ----------

from pyspark.sql.types import *
from pyspark.sql.functions import *

from pyspark.sql import SparkSession

# COMMAND ----------

# DBTITLE 1,Link data from data storage
appName = "PySpark open JSON line"
master = "local"

# Create Spark session
spark = SparkSession.builder \
    .appName(appName) \
    .master(master) \
    .getOrCreate()

# Create data frame
json_file_path = "abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/javascript/small_data.jsonl"
data_reader = spark.read.json(json_file_path)

# COMMAND ----------

display(data_reader)

# COMMAND ----------

# DBTITLE 1,Load dataset
dataset = data_reader.collect()
assert len(dataset) == 100000

# COMMAND ----------

# MAGIC %run ./processing_notebook

# COMMAND ----------

n_thread = 4
split = 16
# data_path = "abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/javascript/small_data.jsonl"
save_path = "abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/javascript/"

# COMMAND ----------

processing(dataset=dataset, save_path=save_path, n=n_thread, split=split)

# COMMAND ----------

!python processing.py \
-n 4 -s 100 \
--cache_path "abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/javascript/small_data.jsonl" \
--save_path "abfss://ai4code@ai4codedatalake.dfs.core.windows.net/small_100k_dataset/javascript/"

# COMMAND ----------

!lscpu | egrep 'Model name|Socket|Thread|NUMA|CPU\(s\)|CPI Core'

# COMMAND ----------


