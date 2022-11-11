import json
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Any, Union

import tree_sitter
from tree_sitter import Language, Parser

from src.utils.noise_detection import clean_comment, strip_c_style_comment_delimiters
from src.utils.noise_removal.noise_removal import check_function
from src.utils.parser.language_parser import match_from_span, tokenize_code, tokenize_docstring, traverse_type


ROOT_PATH = str(Path(__file__).parents[2])

logger = logging.getLogger('utils')
logging.basicConfig(level = logging.INFO)


def build_language(language: str, save_path: str=ROOT_PATH):
    """
    Build tree-sitter language
    
    Args:
        language (str): java, python, cpp, c_sharp, etc
        save_path (str): save path (default to /tree-sitter/)
    """
    ts_path = os.path.join(save_path, 'tree-sitter')
    ts_lang_path = os.path.join(ts_path, 'tree-sitter-'+language)
    if not os.path.exists(ts_path):
        logger.info(
            f"Not found tree-sitter folder, create new one in {ts_path}"
        )
        os.mkdir(ts_path)
    if not os.path.exists(ts_lang_path):
        logger.info(
            f"Not found tree-sitter-{language}, attempt clone from github"
        )
        command = f"cd tree-sitter; git clone https://github.com/tree-sitter/tree-sitter-{language}.git"
        subprocess.Popen(command ,shell=True).wait()
        
        assert os.path.exists(ts_lang_path)==True, f"Unable to find {language} tree-sitter"
        
    lang_path = os.path.join(save_path, 'tree-sitter', f'{language}.so')
    if not os.path.exists(lang_path):
        logger.info(
            f"Attempt to build Tree-sitter Language for {language} and store in {lang_path}"
        )
        Language.build_library(lang_path, [ts_lang_path])
        assert os.path.exists(lang_path)==True
        
    
def parse_code(raw_code: str, language: str) -> tree_sitter.Tree:
    """
    Auto parse raw code into `tree_sitter.Tree`
    
    Args:
        raw_code (str): Raw source code need to parse
        language (str): Language to load parser
    """
    # TODO: auto detect language
    
    language = str(language).lower()
    if language == 'c#':
        language = 'c_sharp'
    elif language == 'c++':
        language = 'cpp'
            
    ts_lang_path = os.path.join(ROOT_PATH, 'tree-sitter', f'{language}.so')
    if not os.path.exists(ts_lang_path):
        build_language(language)
        
    parser = Parser()
    language = Language(ROOT_PATH + f"/tree-sitter/{language}.so", language)
    parser.set_language(language)
    
    if isinstance(raw_code, str):
        tree = parser.parse(bytes(raw_code, 'utf8'))
        return tree
    else:
        return


def process_raw_node(tree: List, blob: str, language_parser, is_class=False):
    """
    Process all extractable functions or class
    Args:
        tree (tree_sitter.Tree): Tree AST of source code
        blob (str): source code
    Returns:
        List contains these keys
            - 'identifier'
            - 'parameter_list'
            - 'code'
            - 'code_tokens'
            - 'original_docstring'
            - 'docstring_tokens'
            - 'comment'
    """
    if not isinstance(tree, tree_sitter.Tree):
        raise ValueError(f'Expect `List` type, get {type(tree)}')
    
    if is_class:
        node_list = language_parser.get_class_list(tree.root_node)
    else:
        node_list = language_parser.get_function_list(tree.root_node)

    outputs = []
    for function in node_list:
        if is_class:
            fn_metadata = language_parser.get_class_metadata(function, blob)
        else:
            fn_metadata = language_parser.get_function_metadata(function, blob)

        if check_function(function, fn_metadata, is_class):
            outputs.append([function, fn_metadata])
        else:
            continue
    
    for function, fn_metadata in outputs:
        # TODO: get class name to compare if function is class's constructor
        comment_nodes = language_parser.get_comment_node(function)
        docstring = language_parser.get_docstring(function, blob)
        code = match_from_span(function, blob)
        code_tokens = tokenize_code(function, blob, comment_nodes)
        
        comment_list = [strip_c_style_comment_delimiters(match_from_span(cmt, blob)) for cmt in comment_nodes]
        
        if docstring == '' or docstring is None:
            docstring = None
            docstring_tokens = None
        else:
            docstring_tokens = tokenize_docstring(docstring)
        
        fn_metadata.update({
            'code': code,
            'code_tokens': code_tokens,
            'original_docstring': docstring,
            'docstring_tokens': docstring_tokens,
            'comment': comment_list
        })
        
        yield fn_metadata
        
        
def get_node_definitions(metadata: List, blob: str) -> List:
    """
    Filter non-quality node by docstring 
    Args:
        metadata (List): List of function or class metadata
        blob (str): source code
    Returns:
        List contains these keys
            - 'identifier'
            - 'parameter_list'
            - 'code'
            - 'code_tokens'
            - 'original_docstring'
            - 'docstring'
            - 'docstring_tokens'
            - 'comment'
    """
    for node_metadata in metadata:
        code = node_metadata['code']
        docstring = node_metadata['original_docstring']
        docstring_tokens = node_metadata['docstring_tokens']
        
        if docstring == None:
            continue
        if len(docstring_tokens) <= 3 or len(docstring_tokens) >= 256:
            continue
        
        docstring = clean_comment(docstring, code)
        if docstring == None:  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
            continue
        
        # TODO: replace clean_comment with check_docstring
        # if check_docstring(docstring):
        #     continue
        
        node_metadata['docstring'] = docstring
        node_metadata['docstring_tokens'] = tokenize_docstring(docstring)
        
        yield node_metadata
        

def get_line_definitions(tree, blob: str, language_parser):
        """
        Process all extractable functions or class
        Args:
            tree (tree_sitter.Tree): AST of the source code
            blob (str): source code
        Returns:
            List contains these keys
                - 'identifier'
                - 'code'
                - 'code_tokens'
                - 'prev_context'
                - 'next_context'
                - 'start_point'
                - 'end_point'
                - 'original_comment'
                - 'comment'
                - 'comment_tokens'
        """
        function_list = language_parser.get_function_list(tree.root_node)
        
        for function_node in function_list:
            comment_nodes = language_parser.get_comment_node(function_node)
            
            if not comment_nodes:
                continue
            
            comment_metadata = {
                'identifier': language_parser.get_function_metadata(function_node, blob)['identifier'],
                'code': match_from_span(function_node, blob),
                'code_tokens': tokenize_code(function_node, blob, comment_nodes),
            }
            
            fn_line_start = function_node.start_point[0]
                
            for comment_node in comment_nodes:
                _comment_metadata = comment_metadata.copy()
                
                comments = [match_from_span(comment_node, blob)]
                prev_node = comment_node.prev_sibling
                next_node = comment_node.next_sibling
                
                _comment_metadata['prev_context'] = None
                _comment_metadata['next_context'] = None
                _comment_metadata['start_point'] = list(comment_node.start_point) #[0] - fn_line_start, comment_node.start_point[1]]
                _comment_metadata['end_point'] = list(comment_node.end_point) #[0] - fn_line_start, comment_node.end_point[1]]
                
                if prev_node is not None:
                    while prev_node.type == 'comment':
                        comments.insert(0, match_from_span(prev_node, blob))
                        _comment_metadata['start_point'] = list(prev_node.start_point)
                        if prev_node.prev_sibling is None: 
                            break
                        prev_node = prev_node.prev_sibling

                    if not prev_node.type == ":":
                        _comment_metadata['prev_context'] = {
                            'code': prev_node.text.decode(),
                            'start_point': list(prev_node.start_point), #[0] - fn_line_start, prev_node.start_point[1]],
                            'end_point': list(prev_node.end_point) # - fn_line_start, prev_node.end_point[1]]
                        }
                
                if next_node is not None:
                    while next_node.type == 'comment':
                        comments.append(match_from_span(next_node, blob))
                        _comment_metadata['end_point'] = list(next_node.start_point)
                        if next_node.next_sibling is None:
                            break
                        next_node = next_node.next_sibling    
                        
                    if next_node.type == "block":
                        next_node = next_node.children[0] if len(next_node.children) > 0 else None
                        
                    _comment_metadata['next_context'] = {
                        'code': next_node.text.decode(),
                        'start_point': [next_node.start_point[0] - fn_line_start, next_node.start_point[1]],
                        'end_point': [next_node.end_point[0] - fn_line_start, next_node.end_point[1]],
                    }
                
                _comment_metadata['start_point'][0] -= fn_line_start
                _comment_metadata['end_point'][0] -= fn_line_start
                
                _cmt = '\n'.join(comments)
                comment = clean_comment(_cmt)
                if comment == None:
                    continue
                
                _comment_metadata['original_comment'] = _cmt
                _comment_metadata['comment'] = comment
                _comment_metadata['comment_tokens'] = tokenize_docstring(comment)
                
                yield _comment_metadata


def write_jsonl(data, save_path: str):
    with open(save_path, "a") as file:
        for item in data:
            json.dump(item, file, ensure_ascii=False)
            file.write('\n')


if __name__ == '__main__':
    lang_list = ['python', 'cpp', 'java', 'c-sharp', 'ruby', 'rust', 'javascript', 'php', 'go']
    
    for lang in lang_list:
        build_language(lang)


    