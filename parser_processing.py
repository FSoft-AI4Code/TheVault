import os
import re
import json
from typing import List

from tree_sitter import Language, Parser

SUPPORTED_LANGUAGES = [ "C#", "C++",  "Java", "JavaScript", "Python",]

FUNCTION_PARSER = ["function_definition", "template_function", "method_declaration", "expression_statement"]
CLASS_PARSER = ["class_declaration", "class_definition", "class_specifier", "struct_specifier"]
COMMENT_PARSER = ["comment", "block_comment"]


DOCSTRING_REGEX_TOKENIZER = re.compile(r"[^\s,'\"`.():\[\]=*;>{\}+-/\\]+|\\+|\.+|\(\)|{\}|\[\]|\(+|\)+|:+|\[+|\]+|{+|\}+|=+|\*+|;+|>+|\++|-+|/+")


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
        

def import_language_parser():
    list_dir = os.listdir('./languages')
    list_dir.remove('my-languages.so')
    print(list_dir)
    lang_list = [str(x).removeprefix('tree-sitter-').replace('-', '_') for x in list_dir]
    tree_lang_list = [os.path.join('./languages', x) for x in list_dir]
    
    
    if not os.path.exists('languages/my-languages.so'):  # build tree
        Language.build_library('languages/my-languages.so', tree_lang_list)
    
    tree_dict = {lang:Language('languages/my-languages.so', lang) for lang in lang_list}
    return tree_dict
    
    
def traverse_type(node, results, kind:List) -> None:
    if node.type in kind:
        results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_type(n, results, kind)
        
        
def find_kind_have_comment(node, kind:List) -> List:
    nodes, function_node = [], []
    function_comment = []
    traverse_type(node, function_node, kind)
    
    
    if not function_node: return None, None
    for func in function_node:
        comments = []
        traverse_type(func, comments, COMMENT_PARSER)
        if comments:
            # print(comments)
            nodes.append(func)
            function_comment.append(comments)
    
    # print(nodes)
    # print(function_comment)
    assert len(nodes) == len(function_comment)
    return nodes, function_comment


def export_data_to_file(data, kind_list, comment_list, language, save_file, type_name='function'):
    for idx, func in enumerate(kind_list):
        name = func.child_by_field_name('name')
        func_name = "None" if name is None else name.text.decode()
        cmts = comment_list[idx]
        cmts_tokens = []
        
        code = remove_comment_from_code(func.text.decode(), cmts)
        code_tokens = tokenize_code(func, cmts)
        for cmt in cmts:
            processed_cmt = tokenize_docstring(cmt.text.decode())
            cmts_tokens.append(processed_cmt)
        cmts = [x.text.decode() for x in comment_list[idx]]
            
        output = data.copy()
        output[f'{type_name}_name'] = func_name
        output[f'{type_name}_comment'] = cmts
        output['code'] = code
        output['code_tokens'] = code_tokens
        output['comment_tokens'] = cmts_tokens
        
        with open(os.path.join(save_file, f"{language}_{type_name}.jsonl"), "a") as outfile:
            json_object = json.dump(output, outfile)
            outfile.write('\n')
            
            
def extract_code_to_tree(data, tree_dict):
    processed_data = {
        "repo_name": data["repo_name"],
        "path": data["path"],
        "language": data["language"],
        "license": data["license"],
        "size": data["size"]
    }
    language = str(data["language"]).lower()
    if language == "c++": language = "cpp"
    if language == "c#": language = "c_sharp"
    
    save_file = f"./data/{language}"
    if not os.path.exists(save_file): os.mkdir(save_file)
    
    parser = Parser()
    parser.set_language(tree_dict[str(language).lower()])
    
    # tree parser
    tree = parser.parse(bytes(data["code"], "utf8"))
    root_tree = tree.root_node
    
    function_list, fcmt_list = find_kind_have_comment(root_tree, FUNCTION_PARSER)
    class_method_list, ccmt_list = find_kind_have_comment(root_tree, CLASS_PARSER)
    
    if function_list:
        export_data_to_file(processed_data, function_list, fcmt_list, language, save_file, 'function')
    if class_method_list:
        export_data_to_file(processed_data, class_method_list, ccmt_list, language, save_file, 'class')
            
    # travese though function but if it has comment
    # remove comment
    

if __name__ == '__main__':
    data_dir = './data/raw/'
    
    tree_dict = import_language_parser()
    
    list_datafile = os.listdir(data_dir)
    for file in list_datafile:
        with open(os.path.join(data_dir, file), 'r') as json_file:
            json_list = list(json_file)
        
        for idx, json_str in enumerate(json_list):
            line = json.loads(json_str)  # each line is 1 source code file

            extract_code_to_tree(line, tree_dict)
            # if idx > 5:
            #     break
        # break
    
    