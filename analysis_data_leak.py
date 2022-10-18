import argparse
import json
import os
from tqdm import tqdm
import pandas as pd

def args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--language', type=str, default='python')
    return parser.parse_args()

opt = args()
language = opt.language

data_path = f'/media/Z/dungnm31/small_500k_dataset/{language}/function_data.jsonl'
save_path = f'/media/Z/dungnm31/small_500k_dataset/ver0.2/{language}/'

if not os.path.exists(save_path):
    os.mkdir(save_path)

with open(data_path, 'r') as json_file:
    dataset = list(json_file)

ds_len = len(dataset)
id_len = len(str(ds_len))
metadata_list = []

index_list = ['python', 'java', 'javascript', 'ruby', 'go', 'php', 'c', 'cpp', 'c_sharp', 'rust']
index_map = {key:val for val, key in enumerate(index_list)}

code_base = set()
docstring_base = set()

for i in tqdm(range(ds_len)):
    data = json.loads(dataset[i])
    id = f"{index_map[language]}1{str(i).zfill(id_len)}"
    
    new_data = {}
    new_data['id'] = id
    new_data.update(data)
    
    code = ''.join(data['code_tokens'])
    docs = data['original_docstring']
    
    if docs not in docstring_base and code not in code_base:
        docstring_base.add(docs)
        code_base.add(code)
        metadata_list.append(new_data)
    
    # metadata = {'repo': repo, 'n_sample': 1, 'set': None}
    # df2 = pd.DataFrame([metadata])
    # df = pd.concat([df, df2], ignore_index = True)

        
    #     # df.loc[df['id'] == idx]['n_sample'] += 1
    #     df.loc[df['repo'] == repo, 'n_sample'] += 1

with open(os.path.join(save_path, f'filterd_function_data.jsonl'), "a") as outfile:
    for function in tqdm(metadata_list):
        json.dump(function, outfile, ensure_ascii=False)
        outfile.write('\n')

# df = pd.DataFrame(metadata_list, columns=['id', 'repo', 'path', 
#                                           'language', 'path', 'license', 'func_name', 'code', 
#                                           'code_tokens', 'original_docstring', 'docstring',
#                                           'docstring_tokens', 'docstring_params'])
# df.to_csv(os.path.join(save_path, 'dataset.csv'))

            
        
    
    

