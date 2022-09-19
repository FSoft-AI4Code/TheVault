# Databricks notebook source
# MAGIC %md # Test

# COMMAND ----------

# DBTITLE 1,Test parser
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

# DBTITLE 1,Test tree_sitter
from tree_sitter import Language, Parser

# COMMAND ----------

# !gdown --id 1rFQkqzKtFfT5iWMioMUZFOxxiY7C6Yq8

!mv /usr/lib/x86_64-linux-gnu/libstdc++.so.6  /usr/lib/x86_64-linux-gnu/libstdc++.so.6.1
!cp libstdc++.so.6.0.29 /usr/lib/x86_64-linux-gnu/

!mv /usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.29  /usr/lib/x86_64-linux-gnu/libstdc++.so.6
!export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/libstdc++.so.6

!cp libstdc++.so.6.0.29 /databricks/conda/lib/
!mv /databricks/conda/lib/libstdc++.so.6.0.29  /databricks/conda/lib/libstdc++.so.6

# COMMAND ----------

import os
list_dir = os.listdir('languages/')
    
print(list_dir)


# COMMAND ----------

lang_list = ['python', 'java', 'javascript']

tree_dict = {lang:Language('languages/my-languages.so', lang) for lang in lang_list}

print(tree_dict)

# COMMAND ----------

parser = Parser()
parser.set_language(tree_dict['java'])

# COMMAND ----------

code = """public class Main {
  public static void main(String[] args) {
    System.out.println(Math.min(5, 10));  
  }
}

"""
tree = parser.parse(bytes(code, "utf8"))
root_tree = tree.root_node

# COMMAND ----------

root_tree.sexp()

# COMMAND ----------

# MAGIC %md # Mount data

# COMMAND ----------

container = "ai4code"
# folder_name = "dataset/python"
accountname = "ai4codedatalake"

def mount_data(folder_name, accountname = "ai4codedatalake", container = "ai4code"):
    apikey = "W7G9tBs7aRVoce1sj2p8mAfYKniUaMUmHh3zs82H8EFA9pUyvBfMnlAc8LHET5vZD90v/FZar4od+AStZTNtfg=="
    #ClientId, TenantId and Secret is for the Application(ADLSGen2App) was have created as part of this recipe
    clientID ="61ce96be-5a4d-4f9f-ade0-9cddd220cfd9"
    tenantID ="f01e930a-b52e-42b1-b70f-a8882b5d043b"
    clientSecret ="OcI8Q~4WAu-eY-gjcMDCfCHy-r.qvyfv5-uETdfA"
    oauth2Endpoint = "https://login.microsoftonline.com/{}/oauth2/token".format(tenantID)


    mountpoint = "/mnt/" + folder_name
    storageEndPoint ="abfss://{}@{}.dfs.core.windows.net/{}/".format(container, accountname, folder_name)
    print ('Mount Point ='+mountpoint)


    configs = {"fs.azure.account.auth.type": "OAuth",
               "fs.azure.account.oauth.provider.type": "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider",
               "fs.azure.account.oauth2.client.id": clientID,
               "fs.azure.account.oauth2.client.secret": clientSecret,
               "fs.azure.account.oauth2.client.endpoint": oauth2Endpoint}

    try:
        dbutils.fs.mount(
        source = storageEndPoint,
        mount_point = mountpoint,
        extra_configs = configs)
        print("New Mount!")
    except:
        print("Update Mount!")
        dbutils.fs.updateMount(
        source = storageEndPoint,
        mount_point = mountpoint,
        extra_configs = configs)

# COMMAND ----------

folder_name = 'small_100k_dataset'
mount_data(folder_name)

# COMMAND ----------

# MAGIC %md # Execution

# COMMAND ----------

account_name = "ai4codedatalake"
apikey = "W7G9tBs7aRVoce1sj2p8mAfYKniUaMUmHh3zs82H8EFA9pUyvBfMnlAc8LHET5vZD90v/FZar4od+AStZTNtfg=="

# session configuration
spark.conf.set(f"fs.azure.account.key.{account_name}.dfs.core.windows.net", apikey)

# COMMAND ----------

# DBTITLE 1,Load dataset
data_reader = spark.read.format('json').load('dbfs:/mnt/small_100k_dataset/small_dataset/javascript/small_data.jsonl')
# data_reader = spark.read.format('json').load('dbfs:/mnt/small_500k_dataset/javascript/small_data.jsonl')

# COMMAND ----------

display(data_reader)

# COMMAND ----------

dataset = data_reader.collect()

# COMMAND ----------

# DBTITLE 1,Run extract
# MAGIC %run ./processing_notebook

# COMMAND ----------

n_thread = 96
split = 96
save_path = "dbfs:/mnt/small_100k_dataset/result" 
# save_path = "/tmp/"

# COMMAND ----------

processing(dataset=dataset, save_path=save_path, n=n_thread, split=split)

# COMMAND ----------

dbutils.fs.cp(f"file:/tmp/function_data.jsonl", "dbfs:/mnt/small_100k_dataset/result/function_data.jsonl", True)

# COMMAND ----------

# DBTITLE 1,Mount
folder_name = 'small_100k_dataset'
mount_data(folder_name)

# COMMAND ----------


