import re
import os
import logging
import json
import time
from pathlib import Path
from itertools import repeat

from tqdm import tqdm
import multiprocessing

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from codetext.clean import remove_comment_delimiters
from codetext.parser.language_parser import tokenize_docstring

logger = logging.getLogger()

class AnalyserWarpper:
    """
    Interface of analyser
    """
    
    def __init__(self, args) -> None:
        self.data_path = args.data_path
        self.save_path = args.save_path
        self.core = args.core
    
    def split(self, ) -> None:
        raise NotImplementedError
    
    def merge(self, ) -> None:
        raise NotImplementedError
    
    def summary(self, ) -> None:
        raise NotImplementedError
    
    def analysing(self, ) -> None:
        raise NotImplementedError
    
    
class Analyser(AnalyserWarpper):
    """
    TODO: Update later
    """
    
    def __init__(self, args) -> None:
        super().__init__(args)
        self.is_file = args.is_file
        self.load_metadata = args.load_metadata
        list_file = []
        if not self.is_file:
            for i in os.listdir(self.data_path):
                if i.endswith('.jsonl'): 
                    list_file.append(os.path.join(self.data_path, i))
            self.list_file = list_file

        # TODO: add 'folk', 'star' and 'issue' as analysis factor 
        self.keys = [ 'repo', 'code', 'docstring']
                    # 'attribute'] # folk, star, issue

        # 'repo_path', 'code' and 'docstring' is used for prevent data leak
        # 'code_length', 'description_length' and 'attribute' is used for
        # balanced spliting as splitting factor
        self.columns = ['repo_path', 'code', 'docstring', \
            '#code', '#docstring', '#comment', '#blank', \
            '#len_code', '#len_docstring', '#len_comment', '#attribute']
        
    def merge(self) -> None:
        assert self.is_file != True
        pool = multiprocessing.Pool(processes=self.core)
        
        time_execute = 0
        for result in tqdm(pool.starmap(self.merge_file, \
                                        zip(repeat(self.save_path), self.list_file)), \
                                        total=len(self.list_file)):
            time_execute += result
        
        pool.close()
        pool.join()
        logger.info(f'Finish merged all jsonl file in {time_execute:.3f}s')
        
    @staticmethod
    def merge_file(save_path: str, file: str) -> float:
        start = time.time()
        with open(file, 'r') as json_file:
            dataset = list(json_file)

        with open(save_path, 'a') as output_file:
            for idx, data in enumerate(dataset):
                try:
                    data = json.loads(data)
                except Exception as e:
                    logger.error(f"An error occurred `{e}`")
                
                json.dump(data, output_file)
                output_file.write('\n')
        end = time.time()
        return end - start
    
    def analysing(self) -> None:
        if self.load_metadata:
            logger.info(f"Loading metadata from {self.load_metadata}")
            assert os.path.isfile(self.load_metadata)
            self.metadata = pd.read_csv(self.load_metadata, index_col=0)
        
        else:
            logger.info(f"Preparing metadata")
            if self.is_file:
                with open(self.data_path, 'r') as json_file:
                    dataset = list(json_file)

                index_list = range(len(dataset))
                chunk_size = len(dataset)//self.core
                jobs = [
                    index_list[x:x+chunk_size] for x in range(0, len(dataset), chunk_size)]
                jobs_list = []
                logger.info(f"Analyzing {Path(self.data_path).name} in total {len(jobs)} processes")
                for job_index in jobs:
                    jobs_list.append([dataset, job_index])
                    
            else:
                # load into multiple process to read
                dataset = []
                jobs_list = self.list_file
                logger.info(f"Found {len(jobs_list)} jsonl file to analysis")
            
            # while reading, append sample's metadata to self.metadata
            pool = multiprocessing.Pool(processes=self.core)
            results = []
            for result in pool.starmap(self.read_json, zip(repeat(dataset), jobs_list)):
                results.extend(result)

            logger.info(f"Export result to {self.save_path}")
            self.metadata = pd.DataFrame(results, columns=self.columns)
            
            # export summary to .csv
            self.metadata.describe().to_csv(os.path.join(self.save_path, 'summary.csv'))
            self.metadata.to_csv(os.path.join(self.save_path, 'analysis_results.csv'))
        
        numberic_col = self.metadata.iloc[:, 3:].columns
        
        self.export_boxplot(numberic_col, os.path.join(self.save_path, 'A.png'))
        self.export_hist(numberic_col, os.path.join(self.save_path, 'B.png'))
    
    def read_json(self, dataset, task):
        s = 'Analyzing '
        if not dataset:  # then read from path and processing
            assert type(task) == str
            assert os.path.isfile(task) == True
            s += str('file: ' + Path(task).name)
            with open(task, 'r') as json_file:
                dataset = list(json_file)
            task = range(len(dataset))
        else:
            s += f'from main file: {task}'
        
        result = []
        for idx in task:
            data = dataset[idx]
            data = json.loads(data)
            
            meta = []
            for key in self.keys:
                assert key in data.keys(), f'Missing `{key}` field'
                if not data[key] or data[key] == '':
                    meta.append(None)
                else:
                    meta.append(str(data[key]).replace('|',''))
            
            code = data['code']
            docstring = data['docstring']
            docstring_param = data['docstring_params']
            comment_node = data['comment']
            
            # file's statistic
            code_line = 0
            blank_line = 0
            comment_line = 0
            docstring_line = 0
            len_comment = 0
            len_code = len(data['code_tokens'])
            len_docstring = len(data['docstring_tokens'])
            
            # TODO: count number of special token, alphabet %, plot outlier 
            
            # count number of code, blank, comment number of line
            for line in str(code).splitlines():
                line = line.strip()
                if line == '':
                    blank_line += 1
                else:
                    if line in comment_node:
                        line = remove_comment_delimiters(line)
                        if line != '': 
                            comment_line += 1
                            len_comment += len(tokenize_docstring(line))
                    else:
                        code_line += 1
            # count number of docstring line
            if not docstring or docstring == '':
                docstring = ''
            else:
                docstring = remove_comment_delimiters(docstring)
            non_blank_docline = [1 if line != '' else 0 \
                for line in str(docstring).splitlines()]
            docstring_line = sum(non_blank_docline)
            
            # count number of attribute
            attribute = 0
            for key, val in docstring_param.items():
                for item in val:
                    if item['docstring'] != None:
                        attribute += 1
                        
            # custom filter
            if code_line > 500: continue
            elif len_code > 1000: continue
            
            
            # columns: '#code', '#docstring', '#comment', '#blank',
            # '#len_code', '#len_docstring', '#len_comment', '#attribute'
            meta.extend([code_line, docstring_line, comment_line, blank_line, \
                        len_code, len_docstring, len_comment, attribute])
            result.append(meta)
        
        return result

    def export_boxplot(self, inputs, save_path=None):
        plt.clf()
        fig, ax = plt.subplots(nrows=8, ncols=1)
        for idx, column in enumerate(inputs):
            self.metadata[column].plot.box(vert=False, figsize=(20,10), ax=ax[idx])

        plt.suptitle('Boxplot Summary')
        plt.tight_layout()
            
        plt.savefig(save_path)

    def export_hist(self, inputs, save_path=None):
        plt.clf()
        nrow, ncol = 4, 2
        fig, ax = plt.subplots(nrows=nrow, ncols=ncol)
        print(inputs)
        for row in range(nrow):
            for col in range(ncol):
                index = inputs[row*2+col]
                ax[row][col].set_title(f'{index} Distribution', fontsize=10)
                ax[row][col].set_yscale('log')
                self.metadata[index].plot.hist(density=True, color='k', alpha=0.5, \
                    figsize=(12,15), ax=ax[row][col])

        plt.suptitle('Histogram Summary')
        plt.tight_layout()
            
        plt.savefig(save_path)
