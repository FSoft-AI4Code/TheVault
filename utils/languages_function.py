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


def remove_words_in_string(words, string):
    new_string = string
    for word in words:
        new_string = str(new_string).replace(word, '')
    return new_string


class Java_extractor():
    def __init__(self, code, comment, file_name, language='java') -> None:
        self.language = language
        self.param_dict = self.extract_params(code, file_name)
        if not self.param_dict:
            self.metadata = self.extract_comment_without_param(comment)
        
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
            
            if self.language == 'java':
                if len(words) >= 2:  # 1-type, 2-param_name
                    params_dict[words[1]] = {'docstring': ""}
                    params_dict[words[1]] = {'type': words[0]}  #
            else:
                if len(words) >= 2:  # only param
                    params_dict[words[0]] = {'docstring': ""}
            
            params_dict['other_params'] = []
        
        return params_dict
    
    def extract_param_comment(self, comment, param_dict):
        metadata = {}
        regex_str = r"[\r|\n]+\s*(\@+[\w]*)"  # catch @tag at start of a string
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
                # print(line)
                line = remove_words_in_string(['\n', '\r', '\t'], line)
                if re.search(subregex, line):
                    param_tag = line.split(' ')[0] # 0=tag, Normal order(1=type, 2=name)  e.g: @param [String] path
                    param_name = None
                    if line.split(' ')[0] == '@param':
                        for word in line.split(' '):  # find which param in this
                            if word in param_dict.keys():
                                param_name = word  # should find some name
                            
                    if param_name is not None:
                        param_type = re.search(r"\[.*?\]", line).group()  # type in ruby store inside []
                        param_dict[param_name]['type'] = param_type
                        param_dict[param_name]['docstring'] = remove_words_in_string([param_tag, param_name, param_type], line)
                            
                        ## Skip outlier param
                        # if break_line[2] not in param_dict.keys():
                        #     param_dict[break_line[2]] = {}
                        # param_dict[break_line[2]]['type'] = re.search(r"\b\w*", break_line[1]).group()  # remove special symbol
                        
                    else:
                        if line.split(' ')[0] == '@param':
                            list(param_dict[param_name]['other_params']).append(remove_words_in_string([param_tag], line))
                        else:
                            param_dict[param_tag] = remove_words_in_string([param_tag], line)
                else:
                    processed_docstring.append(line)
        except Exception:
            return None
        
        metadata['docstring_params'] = param_dict
        metadata['processed_docstring'] = processed_docstring
        metadata['processed_docstring_tokens'] = tokenize_docstring(' '.join(processed_docstring))
        
        return metadata
    
    def extract_comment_without_param(self, comment,):
        metadata = {}
        metadata['docstring_params'] = {}
        
        regex_str = r"[\r|\n]+\s*(\@+[\w]*)"  # catch @tag at start of a string
        subregex = r"(\@+[\w]*)"  # catch "@word"
        preprocessed = re.split(regex_str, comment)

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
        
        for line in splited_comment:
            line = remove_words_in_string(['\n', '\r', '\t'], line)
            line_tag = re.search(subregex, line)
            if line_tag:
                tag = line_tag.group()
                preprocessed_line = remove_words_in_string([tag], line)
                metadata['docstring_params'][tag] = preprocessed_line

        metadata['processed_docstring'] = comment
        metadata['processed_docstring_tokens'] = tokenize_docstring(comment)
        
        return metadata


class Python_extractor():
    def __init__(self, code, comment, file_name):
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
            words = re.findall(r"\w+", each)
            
            if len(words) >= 1:  # only param; param with type, default value, function, etc
                params_dict[words[0]] = {'docstring': False}
        
        return params_dict

    def extract_param_comment(self, comment, param_list):
        # break long string into line by \n\r
        splitted_string = re.split('\n|\r', comment)
        
        # Type 1: 
        regex_str = r"[\r|\n]+\s*(\:+[\w]*)"
        