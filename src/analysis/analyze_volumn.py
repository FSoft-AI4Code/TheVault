
import os
import json
import multiprocessing
from tqdm import tqdm
# from tqdm.contrib.concurrent import process_map
from time import time

class Volumn_analyzer:
    def __init__(self, cores, languages= None, analyze_attrs= None, save_folder= None):
        if languages is None:
            self.languages = ['python', 'php', 'javascript', 'java', 'c_sharp', 'rust', 'ruby', 'c', 'cpp', 'go']
        else:
            self.languages = languages

        if analyze_attrs is None:
            self.attrs = ['identifier', 'code_tokens', 'docstring_tokens', 'short_docstring_tokens', 'distribution_docstring_attributes', 'repo']
        else:
            self.attrs = analyze_attrs
        
        print("Analyze: ", ", ".join(self.attrs))
        print("Analyze languages: ", ", ".join(self.languages))

        self.save_folder = save_folder
        self.raw_folder = "./raw/{}"
        self.clean_folder = "./clean/{}"
        self.cores = cores
        self.result = {}
        self.distribution = {}
        self.all_tokens = {'docstring_tokens': [], 'code_tokens': [], 'identifier': [], 'short_docstring_tokens': []}

    def get_volumn_infomation(self, datafile):
        with open(datafile, 'r') as json_file:
            dataset = json_file.readlines()

        rs = {"volumn": []}
        for attr in self.attrs:
            rs[attr] = []
        
        rs['volumn'].append(len(dataset))
        if "raw" in datafile:
            rs['none_docstring'] = 0
            for dp in dataset:
                try:
                    dp = json.loads(dp)
                except:
                    continue
                if dp['original_docstring'] is None or dp['original_docstring'].strip() == "":
                    rs['none_docstring'] += 1
            return rs
        
        for dp in dataset:
            dp = json.loads(dp)
            for attr in self.attrs:
                if ((attr != 'distribution_docstring_attributes' and attr not in dp) or             # Some attr is missing in some language
                   (attr == 'distribution_docstring_attributes' and "docstring_params" not in dp)): # e.g. Golang do not have short_docstring_tokens 
                                                                                   
                    rs[attr].append(0)
                    continue

                if attr == 'identifier' or attr == 'repo':
                    rs[attr].append(dp[attr])
                elif attr == 'distribution_docstring_attributes':
                    cnt = 0
                    for doc_param_info in dp["docstring_params"]:
                        cnt += len(dp["docstring_params"][doc_param_info])
                    
                    rs[attr].append(cnt)
                else:
                    rs[attr].extend(dp[attr])
                    if "distribution_" + attr not in rs:
                        rs["distribution_" + attr] = []
                    rs["distribution_" + attr].append(len(dp[attr]))
        return rs

    def analyze_single_lang(self, lang, include_raw):
        print(lang)
        if not os.path.exists(self.clean_folder.format(lang)):
            return

        all_clean_files = [os.path.join(self.clean_folder.format(lang), filename) for filename in os.listdir(self.clean_folder.format(lang)) if "jsonl" in filename]

        pool = multiprocessing.Pool(processes=self.cores)
        
        self.result[lang] = {}
        tmp_rs = {"volumn": []}
        self.distribution[lang] = {}
        for attr in self.attrs:
            tmp_rs[attr] = []

            if "distribution_" not in attr:
                name = "distribution_" + attr
            else:
                name = attr
            self.distribution[lang][name] = []

        chunksize = max(len(all_clean_files)//self.cores, 10)

        for result in tqdm(pool.map(self.get_volumn_infomation, \
                                    all_clean_files, chunksize=chunksize), \
                                    total=len(all_clean_files), desc=f"{lang}: "):
            for attr in result:
                if 'distribution' in attr:
                    self.distribution[lang][attr] += result[attr]
                else:
                    tmp_rs[attr] += result[attr]
        

        self.result[lang]['volumn'] = sum(tmp_rs['volumn'])

        if include_raw:
            tmp_rs["raw_volumn"] = []
            tmp_rs["none_docstring"] = 0
            all_raw_files = [os.path.join(self.raw_folder.format(lang), filename) for filename in os.listdir(self.raw_folder.format(lang)) if "jsonl" in filename]
            for result in tqdm(pool.map(self.get_volumn_infomation, \
                                    all_raw_files, chunksize=chunksize), \
                                    total=len(all_raw_files), desc=f"Raw {lang}: "):
                tmp_rs["raw_volumn"] += result["volumn"]
                tmp_rs["none_docstring"]  += result["none_docstring"]

            self.result[lang]['raw_volumn'] = sum(tmp_rs['raw_volumn'])
            self.result[lang]['none_docstring'] = tmp_rs['none_docstring']
        
        print(f"Collecting ...")

        all_tokens = {'docstring_tokens': [], 'code_tokens': [], 'identifier': [], 'short_docstring_tokens': []}
        for attr in self.attrs:
            if 'distribution' in attr:
                continue
            if "volumn" in attr:
                self.result[lang][attr] = sum(tmp_rs[attr])
            else:
                self.result[lang]["all_" + attr] = len(tmp_rs[attr])
                self.result[lang]["unique_" + attr] = len(set(tmp_rs[attr]))
                if attr in all_tokens:
                    all_tokens[attr].extend(tmp_rs[attr])

        # with open(os.path.join(self.save_folder, f'{lang}_token.json'), "w") as f:
        #         json.dump(all_tokens, f, indent= 4)

        print(f"Finish {lang}!")
        del tmp_rs
        del all_tokens
    

    def analyze(self, include_raw= False):
        for lang in self.languages:
            self.analyze_single_lang(lang, include_raw)

        if self.save_folder is not None:
            with open(os.path.join(self.save_folder, 'statistic.json'), "w") as f:
                json.dump(self.result, f, indent= 4)
            with open(os.path.join(self.save_folder, 'lang_distribution.json'), "w") as f:
                json.dump(self.distribution, f, indent= 4)

if __name__ == "__main__":
    save_folder = "./statistic"
    attr = ['repo']
    attrs = None
    analyzer = Volumn_analyzer(cores=20, save_folder= save_folder)
    analyzer.analyze(include_raw=False)

    for attr in analyzer.all_tokens:
        print(attr, len(set(analyzer.all_tokens[attr])))

    print(analyzer.result)