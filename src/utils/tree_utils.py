import json
import os
import re
from typing import List

from tree_sitter import Language, Parser
from .parser.python_parser import PythonParser

SUPPORTED_LANGUAGES = [ "C#", "C++",  "Java", "JavaScript", "Python",]

FUNCTION_PARSER = ["function_definition", "template_function", "method_declaration"]
CLASS_PARSER = ["class_declaration", "class_definition", "class_specifier", "struct_specifier"]
COMMENT_PARSER = ["comment", "block_comment", "expression_statement"]

DOCSTRING_REGEX = re.compile(r"(['\"])\1\1(.*?)\1{3}", flags=re.DOTALL)
DOCSTRING_REGEX_TOKENIZER = re.compile(r"[^\s,'\"`.():\[\]=*;>{\}+-/\\]+|\\+|\.+|\(\)|{\}|\[\]|\(+|\)+|:+|\[+|\]+|{+|\}+|=+|\*+|;+|>+|\++|-+|/+")


def remove_words_in_string(words, string):
    new_string = string
    for word in words:
        new_string = str(new_string).replace(word, '')
    return new_string


def tokenize_docstring(docstring: str) -> List[str]:
    return [t for t in DOCSTRING_REGEX_TOKENIZER.findall(docstring) if t is not None and len(t) > 0]


def tokenize_code(node, nodes_to_exclude=None) -> List:
    tokens = []
    traverse(node, tokens)
    return [token.text.decode() for token in tokens if nodes_to_exclude is None or token not in nodes_to_exclude]


def remove_comment_from_code(code, comment_list):
    processed_code = str(code)
    for cmt in comment_list:
        cmt = cmt.text.decode()
        processed_code.replace(cmt, '')
        
    return processed_code


def traverse(node, results: List) -> None:
    if node.type == 'string':
        results.append(node)
        return
    for n in node.children:
        traverse(n, results)
    if not node.children:
        results.append(node)


def traverse_commment(node, results, parser) -> None:
    if node.type in parser:
        if node.type == 'expression_statement':
            text = remove_words_in_string(['\r','\n'], node.text.decode())
            if DOCSTRING_REGEX.search(text):
                results.append(node)
        else:
            results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_commment(n, results, parser)

    
def traverse_type(node, results, kind:List) -> None:
    if node.type in kind:
        results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_type(n, results, kind)


def import_language_parser():
    list_dir = os.listdir('./languages')
    
    print(list_dir)
    lang_list = [str(x).removeprefix('tree-sitter-').replace('-', '_') for x in list_dir]
    
    if 'my_languages.so' not in lang_list:
        tree_lang_list = [os.path.join('./languages', x) for x in list_dir]
        Language.build_library('languages/my-languages.so', tree_lang_list)
       
    else:
        lang_list.remove("my_languages.so")
        
    lang_list = ['python', 'java', 'javascript', 'php', 'c_sharp', 'ruby', 'go', 'cpp']

    tree_dict = {lang:Language('languages/my-languages.so', lang) for lang in lang_list}
    
    print(tree_dict)
    return tree_dict


def find_kind_have_comment(node, kind:List, comment_parse:List=COMMENT_PARSER) -> List:
    function_node, function_comment = [], []
    traverse_type(node, function_node, kind)
    # print(function_node)
    
    if not function_node: return None, None  # Empty
    for func in function_node[:]:
        comments = []
        traverse_commment(func, comments, comment_parse)
        # print(comments)
        
        # cursor = func.walk()  # comment in last line
        # cursor.goto_next_sibling()
        
        # if cursor.node.type in ['comment', 'block_comment']:
        #     comments.append(cursor.node)
        
        if not comments:
            function_node.remove(func)
        else:
            function_comment.append(comments)
    
    # print(function_node)
    
    return function_node, function_comment


def reformat_function_data(info, metadata_list) -> List:
    data_list = []
    for fn in metadata_list:
        output = info.copy()
        output['func_name'] = fn['identifier']
        output['code'] = fn['function']
        output['code_tokens'] = fn['function_tokens']
        output['original_docstring'] = fn['original_docstring']
        output['docstring'] = {'block_comment': fn['docstring'] if fn['docstring'] != "" else None, 
                               'line_comment': fn['comment'] if fn['comment'] else None}
        output['docstring_tokens'] = fn['docstring_tokens']
        output['docstring_params'] = fn['docstring_param']
        
        data_list.append(output)
    
    return data_list


def reformat_class_data(info, metadata_list) -> List:
    data_list = []
    for fn in metadata_list:
        output = info.copy()
        output['class_name'] = fn['identifier']
        output['code'] = fn['class']
        output['code_tokens'] = fn['class_tokens']
        output['original_docstring'] = fn['original_docstring']
        output['docstring'] = fn['docstring']
        output['docstring_tokens'] = fn['docstring_tokens']
        output['docstring_params'] = fn['docstring_param']
        
        data_list.append(output)
    
    return data_list

  
def reformat_line_data(info, metadata_list) -> List:
    data_list = []
    for fn in metadata_list:
        output = info.copy()
        output['parent_name'] = fn['identifier']
        output['code'] = fn['function']
        output['code_tokens'] = fn['function_tokens']
        output['prev_context'] = fn['prev_context']
        output['next_context'] = fn['next_context']
        output['original_comment'] = fn['original_comment']
        output['start_point'] = fn['start_point']
        output['end_point'] = fn['end_point']
        output['comment'] = fn['comment']
        output['comment_tokens'] = fn['comment_tokens']
        
        data_list.append(output)
    
    return data_list    

def export_data_to_file(data, kind_list, comment_list, type_name='function'):
    data_list = []
    assert len(kind_list) == len(comment_list)
    for idx, func in enumerate(kind_list):
        output = data.copy()
        name = func.child_by_field_name('name')
        func_name = "None" if name is None else name.text.decode()
        # print('LEN', len(comment_list), idx)
        comments = comment_list[idx]
        comment_tokens = set()
        docstring_list = {'block_comment': [], 'line_comment': []}
        
        code = func.text.decode()
        output[f'{type_name}_name'] = func_name
        output['original_string'] = code
        code_tokens = tokenize_code(func, comments)  # exclude comment line and block
        comments = [x.text.decode() for x in comments]
        
        code = remove_words_in_string(comments, code)

        for token in code_tokens[:]:
            if token in comments:
                code_tokens.remove(token)

        for cmt in comments:
            processed = tokenize_docstring(cmt)
            comment_tokens.update(processed)
            

            if DOCSTRING_REGEX.search(cmt):
                docstring_list["block_comment"].append(cmt)
            else:
                docstring_list["line_comment"].append(cmt)
        
        output['code'] = code
        output['code_tokens'] = code_tokens
        output['docstring'] = docstring_list
        output['docstring_tokens'] = list(comment_tokens)
        
        # with open(os.path.join(save_file, f"{language}_{type_name}.jsonl"), "a") as outfile:
        #     json_object = json.dump(output, outfile)
        #     outfile.write('\n')
        data_list.append(output)
            
    return data_list
            
def extract_code_to_tree(data, tree_dict, save_file):
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
    language = str(data["language"]).lower()
    
    if language == "c++": language = "cpp"
    if language == "c#": language = "c_sharp"
    
    # save_file = f"./data/{language}"
    # if not os.path.exists(save_file): os.mkdir(save_file)
    
    parser = Parser()
    parser.set_language(tree_dict[str(language).lower()])
    
    # tree parser
    raw_code = data["code"]
    tree = parser.parse(bytes(raw_code, "utf8"))
    root_tree = tree.root_node

    function = list(PythonParser.get_function_definitions(root_tree))
    fn_metadata = list(PythonParser.process_functions(function, raw_code))
    
    fn_data = []
    if len(fn_metadata) > 0:
        fn_data = reformat_function_data(processed_data, fn_metadata)
    
    # function_list, fcmt_list = find_kind_have_comment(root_tree, FUNCTION_PARSER)
    # class_method_list, ccmt_list = find_kind_have_comment(root_tree, CLASS_PARSER)
    # print('Function:', function_list)
    
    # func_data, class_data = [], []
    # if function_list:
    #     func_data = export_data_to_file(processed_data, function_list, fcmt_list, 'function')
    # if class_method_list:
    #     class_data = export_data_to_file(processed_data, class_method_list, ccmt_list, 'class')
        
    # return func_data, class_data
    return fn_data
    