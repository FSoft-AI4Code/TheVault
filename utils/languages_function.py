import os
import re
import json
from typing import List
from lizard import analyze_file

from .tokenize import tokenize_docstring


def export_jsonl(data: dict, save_path: str):
    with open(os.path.join(save_path), "a") as outfile:
        json_object = json.dump(data, outfile)
        outfile.write('\n')
        
        
def function_extract(function_code, file_name):
    report = analyze_file.analyze_source_code(file_name, function_code)
    try:
        params = report.function_list[0].full_parameters  # 1 function only
    except IndexError:
        return None
    
    return params


class Java_extractor():
    def __init__(self, code, comment, file_name) -> None:
        self.param_dict = self.extract_params(code, file_name)
        if not self.param_dict:
            self.metadata = {}
            self.metadata['params'] = []
            self.metadata['processed_docstring'] = comment
            self.metadata['processed_docstring_tokens'] = tokenize_docstring(' '.join(comment))
        
        else:
            self.metadata = self.extract_param_comment(comment, self.param_dict)
        
    def extract_params(self, function_code, file_name):
        params = function_extract(function_code, file_name)
        params_dict = {}
        
        if not params:
            return None
        
        for each in params:
            # words = str(each).split(' ')
            words = re.findall(r"\w+", each)
            
            if len(words) >= 1:  # only param or param with type, default value, function
                params_dict[words[0]] = {'docstring': False}
        
        return params_dict
    
    def extract_param_comment(self, comment, param_dict):
        metadata = {}
        regex_str = r"[\r|\n]+\s*(\@+[\w]*)"  # catch @param at start of a string
        subregex = r"(\@+[\w]*)"  # catch "@word"
        preprocessed = re.split(regex_str, comment)
        
        if not param_dict:
            return None

        splited_comment = []
        line = ""
        for sub_str in preprocessed:
            start_symbol = re.search(subregex, sub_str)
            if start_symbol:
                splited_comment.append(line)
                line = start_symbol.group()
            else: 
                line += sub_str
        splited_comment.append(line)
        
        processed_docstring = []
        try:
            for line in splited_comment:
                line = re.search(r".*[^\n\r\t]", line).group()  # remove \n \r \t
                if re.search(subregex, line):
                    break_line = line.split(' ') # 0=tag, 1=type, 2=name  e.g: @param [String] path
                    if break_line[0] == '@param':
                        if break_line[2] not in param_dict.keys():
                            param_dict[break_line[2]] = {}
                        param_dict[break_line[2]]['type'] = re.search(r"\b\w*", break_line[1]).group()
                        param_dict[break_line[2]]['docstring'] = ' '.join(break_line[3:])

                    else:
                        param_dict[break_line[0]] = ' '.join(break_line[1:])
                else:
                    processed_docstring.append(line)
        except Exception:
            return None
        
        metadata['params'] = param_dict
        metadata['processed_docstring'] = processed_docstring
        metadata['processed_docstring_tokens'] = tokenize_docstring(' '.join(processed_docstring))
        
        return metadata
    
        # try:    
        #     for line in splited_comment:
        #         if re.search(regex_str, line):
        #             break_line = line.split(' ')
        #             if break_line[0] == '@param':
        #                 if break_line[1] not in param_dict.keys():
        #                     param_dict[break_line[1]] = {}
        #                 param_dict[break_line[1]]['docstring'] = ' '.join(break_line[2:])

        #             else:
        #                 param_dict[break_line[0]] = ' '.join(break_line[1:])
        #         else:
        #             processed_docstring.append(line)
        # except Exception:
        #     return None
