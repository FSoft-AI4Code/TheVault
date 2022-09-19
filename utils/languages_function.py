import os
import re
import json
from typing import List
from lizard import analyze_file
from docstring_parser import parse

from .tree_utils import remove_words_in_string, tokenize_docstring


def export_jsonl(data: dict, save_path: str):
    with open(save_path, "a") as outfile:
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
            self.metadata = self.extract_comment_without_param(comment)
        else:
            self.metadata = self.extract_param_comment(comment, self.param_dict)
        
        if not self.metadata['docstring_params']['other_params']:
            self.metadata['docstring_params'].pop('other_params', None)
            
    def extract_params(self, function_code, file_name):
        params = function_extract(function_code, file_name)
        params_dict = {}
        
        if not params:
            return None
        
        for each in params:
            words = re.findall(r"\w+", each)
            
            if len(words) >= 1:  # only param; param with type, default value, function, etc
                params_dict[words[0]] = {'docstring': None}
                
            params_dict['other_params'] = {}
        
        return params_dict
    
    def extract_comment_without_param(self, comment):
        metadata = {}
        metadata['docstring_params'] = {'other_params': {}}
        try: 
            docstring = parse(comment)
        except Exception as e:
            return None
        
        for item in docstring.meta:
            if len(item.args) > 0:
                try:
                    tag = item.args[0]
                    param_docstring = remove_words_in_string(['\n', '\r'], str(item.description))
                        
                    if tag == 'param':
                        # if item
                        metadata['docstring_params']['other_params'][tag] = param_docstring
                        
                        # try:
                        if item.type_name is not None:
                            metadata['docstring_params'][tag] = {'docstring': param_docstring, 'type': item.type_name}
                        else: 
                            metadata['docstring_params'][tag] = param_docstring
                    #         # raise Exception
                except Exception:
                    return None

        # description = ''.join([x for x in [docstring.short_description, docstring.long_description] if x != None])
        
        # metadata['docstring'] = description
        # metadata['docstring_tokens'] = tokenize_docstring(comment)
        return metadata
        

    def extract_param_comment(self, comment, param_dict):
        metadata = {}
        comments = []
        try:
            docstring = parse(comment)
        except Exception:
            return None
        
        for item in docstring.meta:
            if len(item.args) > 0:
                try:
                    if item.args[0] == 'param':
                        name = item.arg_name
                        param_type = item.type_name
                        param_default = item.default
                        param_docstring = item.description
                        
                        param_docstring = remove_words_in_string(['\r', '\n'], str(param_docstring))
                        if name in param_dict.keys():
                            param_dict[name]['docstring'] = param_docstring
                            comments.append(param_docstring)
                            if param_type != None:
                                param_dict[name]['type'] = param_type
                            if param_default != None:
                                param_dict[name]['default'] = param_default
                            
                        else:
                            if param_type != None:
                                param_dict['other_params'][name] = {'docstring':param_docstring, 'type': param_type}
                            param_dict['other_params'][name] = param_docstring
                        
                    else:
                        tag = item.args[0]
                        param_docstring = item.description
                        # docstring = remove_words_in_string(['\r', '\n'], str(item.description))
                        if param_docstring != None and param_docstring != "None":
                            try:
                                if item.type_name != None:
                                    param_dict[tag] = {'docstring': param_docstring, 'type': item.type_name}
                                else:
                                    raise Exception
                            except Exception as e:
                            # else:
                                param_dict[tag] = param_docstring
                except Exception:
                    return None

        # description = ' '.join([x for x in [docstring.short_description, docstring.long_description] if x != None])

        metadata['docstring_params'] = param_dict
        # metadata['docstring'] = description
        # metadata['docstring_tokens'] = tokenize_docstring(description)
        
        return metadata
        