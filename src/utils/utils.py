import json
import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Union

import nltk
import tree_sitter
from tree_sitter import Language, Parser

from codetext.utils import module_available
from codetext.clean import remove_comment_delimiters
from codetext.parser.language_parser import match_from_span, match_from_spans, tokenize_code, tokenize_docstring
from utils.noise_removal.noise_removal import check_function, clean_docstring


_DOCSTRING_PARSER_AVAILABLE = module_available("docstring_parser")

ROOT_PATH = str(Path(__file__).parents[3])

logger = logging.getLogger('utils')
logging.basicConfig(level = logging.INFO)

if _DOCSTRING_PARSER_AVAILABLE:
    from docstring_parser.common import *
    from docstring_parser.parser import parse
    STYLE_MAP = {
        'python': [DocstringStyle.REST,
                DocstringStyle.GOOGLE,
                DocstringStyle.NUMPYDOC,
                DocstringStyle.EPYDOC,],
        'java': [DocstringStyle.JAVADOC],
        'javascript': [DocstringStyle.JSDOC],
        'ruby': [DocstringStyle.RDOC],
        'php': [DocstringStyle.PHPDOC],
        'c': [DocstringStyle.JAVADOC],
        'cpp': [DocstringStyle.JAVADOC],
        'go': [],
        'c_sharp': [DocstringStyle.XML,
                    DocstringStyle.JAVADOC],
        'rust': [DocstringStyle.RUSTDOC,
                DocstringStyle.JAVADOC], 
    }
else:
    logger.warning("`docstring_parser` is not available.")


SUPPORTED_LANGUAGE = ['python', 'java', 'javascript', 'ruby', 'go', 'c', 'cpp', 'c_sharp', 'php', 'rust']


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
    
    if language == 'c-sharp': language = 'c_sharp'
    lang_path = os.path.join(save_path, 'tree-sitter', f'{language}.so')
    if not os.path.exists(lang_path):
        logger.info(
            f"Attempt to build Tree-sitter Language for {language} and store in {lang_path}"
        )
        Language.build_library(lang_path, [ts_lang_path])
        assert os.path.exists(lang_path)==True
        
    
def parse_code(raw_code: str, language: str='Auto') -> tree_sitter.Tree:
    """
    Auto parse raw code into `tree_sitter.Tree`
    
    Args:
        raw_code (str): Raw source code need to parse
        language (str): Language to load parser
    """
    # TODO: auto detect language
    if language == 'Auto':
        raise NotImplemented()
    
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
        raise ValueError(f"Expect `str`, got {type(raw_code)}")


def get_first_sentence(paragraph):
    """
    Returns the first sentence of a given paragraph of text.
    """
    # Tokenize the paragraph into sentences
    paragraph = remove_comment_delimiters(paragraph)
    first_para = paragraph.split('\n\n')[0]
    
    sentences = nltk.sent_tokenize(first_para)
    
    # Iterate over the sentences to find the first one that is not empty
    for sentence in sentences:
        if len(sentence.strip()) > 0:
            return sentence.strip()
    
    # If all sentences are empty, return an empty string
    return ''


def process_raw_node(tree, blob: str, language_parser, metadata, is_class=False):
    """
    Process all extractable functions or class
    Args:
        tree (tree_sitter.Tree): Tree AST of source code
        blob (str): source code
        language_parser (LanguageParser): Language parser (`utils/parser`)
        metadata (Dict): file metadata
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
    
    assert isinstance(tree, tree_sitter.Tree), f'Expect tree is `tree_sitter.Tree` type, get {type(tree)}'
    
    try:
        if is_class:
            node_list = language_parser.get_class_list(tree.root_node)
        else:
            node_list = language_parser.get_function_list(tree.root_node)
    except Exception:
        return []

    outputs = []
    for function in node_list:
        try:
            if is_class:
                fn_metadata = language_parser.get_class_metadata(function)
            else:
                fn_metadata = language_parser.get_function_metadata(function)

            if check_function(function, fn_metadata, language_parser.BLACKLISTED_FUNCTION_NAMES, is_class=is_class):
                outputs.append([function, fn_metadata])
            else:
                continue

        except Exception:
            continue
    
    for function, fn_metadata in outputs:
        try:
            comment_nodes = language_parser.get_comment_node(function)
            docstring_node = language_parser.get_docstring_node(function)
            
            exclude_node = []
            if docstring_node:
                exclude_node.extend(docstring_node)
            if comment_nodes:
                exclude_node.extend(comment_nodes)
            
            docstring = language_parser.get_docstring(function)
            code = match_from_span(function, blob)
            code_tokens = tokenize_code(function, blob, exclude_node)
            
            comment_list = [match_from_span(cmt, blob) for cmt in comment_nodes]
            
            # Check length after remove all comment node inside
            code_remove_comment = ''
            for line in str(code).splitlines():
                include = False
                for cline in comment_list:
                    if cline in line:
                        include = True
                if not include:
                    code_remove_comment += f'\n{line}'

            code_remove_comment_line = sum([1 if line != '' else 0 \
                for line in str(code_remove_comment).splitlines()])
            if code_remove_comment_line < 3:
                continue

        except Exception:
            continue
        
        if docstring == '' or docstring is None:
            docstring = None
            docstring_tokens = None
        else:
            docstring_tokens = tokenize_docstring(docstring)
        
        fn_metadata.update(metadata)
        fn_metadata.update({
            'code': code,
            'code_tokens': code_tokens,
            'original_docstring': docstring,
            'comment': comment_list,
            'docstring_tokens': docstring_tokens,
        })
        
        yield fn_metadata
        
        
def get_node_definitions(metadata: List) -> List:
    """
    Filter non-quality node by docstring 
    Args:
        metadata (List): List of function or class metadata
        blob (str): source code
    Returns:
        List[str]: List contains these keys
            - 'identifier'
            - 'parameter_list'
            - 'code'
            - 'code_tokens'
            - 'original_docstring'
            - 'docstring' (new)
            - 'docstring_tokens' (modified)
            - 'comment'
    """
    for node_metadata in metadata:
        code = node_metadata['code']
        docstring = node_metadata['original_docstring']
        docstring_tokens = node_metadata['docstring_tokens']

        if docstring == None:
            continue
        
        # change clean_comment -> clean_docstring
        docstring = clean_docstring(docstring, code)
        if docstring == None:  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
            continue
        
        # No need this one
        # docstring_tokens = tokenize_docstring(docstring)
        # if len(docstring_tokens) <= 3 or len(docstring_tokens) >= 256:
        #     continue
        
        node_metadata['docstring'] = docstring
        node_metadata['docstring_tokens'] = docstring_tokens
        
        yield node_metadata
        

def get_line_definitions(tree, blob: str, language_parser, source_metadata):
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
            
            
            general_metadata = source_metadata
            general_metadata.update({
                'identifier': language_parser.get_function_metadata(function_node)['identifier'],
                'code': match_from_span(function_node, blob),
                'code_tokens': tokenize_code(function_node, blob, comment_nodes),
            })
            
            fn_line_start = function_node.start_point[0]
            
            # remove duplicate sample then extract
            for comment_node in comment_nodes:
                comment_metadata = general_metadata.copy()
                
                comments = [match_from_span(comment_node, blob)]
                prev_node = comment_node.prev_sibling
                next_node = comment_node.next_sibling
                
                comment_metadata['prev_context'] = {}
                comment_metadata['next_context'] = {}
                comment_metadata['start_point'] = list(comment_node.start_point) #[0] - fn_line_start, comment_node.start_point[1]]
                comment_metadata['end_point'] = list(comment_node.end_point) #[0] - fn_line_start, comment_node.end_point[1]]
                
                prev_context = []
                if prev_node:
                    # check if prev_node is comment to append comment list
                    # while prev_node.type == 'comment':
                    #     comments.insert(0, match_from_span(prev_node, blob))
                    #     comment_metadata['start_point'] = list(prev_node.start_point)
                    #     prev_node = prev_node.prev_sibling
                    #     if not prev_node:
                    #         break
                    if prev_node.type == 'comment':
                        continue

                    # if not meet the open bracket
                    while prev_node:
                        prev_context.insert(0, prev_node)
                        prev_node = prev_node.prev_sibling
                        if not prev_node:
                            break
                        elif prev_node.type == 'comment':
                            break
                
                if prev_context:
                    code, top, bottom = match_from_spans(prev_context, blob)
                    comment_metadata['prev_context'] = {
                        'code': code,
                        'start_point': [top.start_point[0] - fn_line_start, top.start_point[1]],
                        'end_point': [bottom.end_point[0] - fn_line_start, bottom.end_point[1]],
                    }
                
                next_context = []
                if next_node:
                    while next_node.type == 'comment':
                        comments.append(match_from_span(next_node, blob))
                        comment_metadata['end_point'] = list(next_node.start_point)
                        next_node = next_node.next_sibling    
                        if not next_node:
                            break
                        
                    # while not meet the other comment or not reach the end node
                    # keep appending
                    while next_node:
                        next_context.append(next_node)
                        next_node = next_node.next_sibling
                        if not next_node:
                            break 
                        elif next_node.type == 'comment':
                            break
                    
                if next_context:
                    code, top, bottom = match_from_spans(next_context, blob)
                    comment_metadata['next_context'] = {
                        'code': code,
                        'start_point': [top.start_point[0] - fn_line_start, top.start_point[1]],
                        'end_point': [bottom.end_point[0] - fn_line_start, bottom.end_point[1]],
                    }
                
                comment_metadata['start_point'][0] -= fn_line_start
                comment_metadata['end_point'][0] -= fn_line_start
                
                _cmt = '\n'.join(comments)
                
                # change clean_comment -> clean_docstring
                comment = clean_docstring(_cmt)
                if comment == None:
                    continue
                
                comment_metadata['original_comment'] = _cmt
                comment_metadata['comment'] = comment
                comment_metadata['comment_tokens'] = tokenize_docstring(comment)
                
                yield comment_metadata


def extract_node(metadata_list, language:str):
    """Get metadata as input and parse docstring into metadata
    
    Args:
        metadata (Dict): Metadata
    
    Returns: 
        Dict[str, Any]: Extracted docstring and metadata, contains:
            - 'identifier'
            - 'parameter'
            - 'code'
            - 'code_tokens'
            - 'original_docstring'
            - 'docstring' (modified)
            - 'docstring_tokens' (modified)
            - 'comment'
            - 'docstring_params' (new)
    """
    assert isinstance(metadata_list, List), f'Expect `List`, get {type(metadata_list)}'
    language = str(language).lower()
    if language == 'c#':
        language = 'c_sharp'
    elif language == 'c++':
        language = 'cpp'
    
    fail_count = 0
    for metadata in metadata_list:
        assert isinstance(metadata, Dict), f'Expect `Dict`, get {type(metadata)}'
        assert language in SUPPORTED_LANGUAGE, f'{language} not supported!'
        for key in ['identifier', 'code', 'code_tokens', 'docstring']:
            assert key in metadata.keys(), f"Expect keyword '{key}'"

        output_metadata = metadata.copy()
        output_metadata.update({
            'identifier': metadata['identifier'],
            'parameters': metadata['parameters'],
            'code': metadata['code'],
            'code_tokens': metadata['code_tokens'],
            'original_docstring': metadata['original_docstring'],
            'comment': metadata['comment']
        })
        docstring = remove_comment_delimiters(metadata['original_docstring'], False)
        extracted_res = extract_docstring(docstring, metadata['parameters'], language)
        if not extracted_res:  # extract fail
            continue
        if extracted_res['docstring'] == '' or not extracted_res['docstring']:
            continue
        output_metadata.update(extracted_res)
        
        if not check_fn_cls_output(output_metadata):
            fail_count += 1
            continue
            
        yield output_metadata
        
    if fail_count > 0:
        logger.info('Failed to extract {} sample'.format(fail_count))


def check_fn_cls_output(output):
    """Output assertion
    
    Check if:
        - 'identifier' is not null
        - 'type' is not null (with C/C++, Java, C# only)
        - 'docstring_param' not contain null docstring
    """
    importance_keys = ['repo', 'path', 'license', 'identifier', 'language', 'code', \
                        'code_tokens', 'comment', 'docstring', 'docstring_tokens', \
                        'docstring_params', 'parameters', 'short_docstring']
    for key in importance_keys:
        assert key in output.keys(), f'Missing {key}'
    assert type(output['repo']) == str, f"Expect str but got {type(output['repo'])}"
    assert type(output['path']) == str, f"Expect str but got {type(output['path'])}"
    assert type(output['language']) == str, f"Expect str but got {type(output['language'])}"
    assert type(output['parameters']) == dict, f"Expect Dict but got {type(output['parameters'])}"
    assert type(output['code']) == str, f"Expect str but got {type(output['code'])}"
    assert type(output['code_tokens']) == list, f"Expect List but got {type(output['code_tokens'])}"
    assert type(output['docstring']) == str, f"Expect str but got {type(output['docstring'])}"
    assert type(output['short_docstring']) == str, f"Expect str but got {type(output['short_docstring'])}"
    assert type(output['short_docstring_tokens']) == list, f"Expect List but got {type(output['short_docstring_tokens'])}"
    assert type(output['docstring_tokens']) == list, f"Expect List but got {type(output['docstring_tokens'])}"
    assert type(output['docstring_params']) == dict, f"Expect Dict but got {type    (output['docstring_params'])}"
    assert output['docstring'] != ''
    assert output['code'] != ''
    
    
    # TODO: add this filter to the post-processing
    
    # code_line = 0
    # code = output['code']
    # docstring = output['docstring']
    # comment_node = output['comment']
    # for line in str(code).splitlines():
    #     line = remove_comment_delimiters(line.strip())
    #     if line != '':
    #         if not line in comment_node:
    #             code_line += 1
    
    # non_blank_docline = [1 if line != '' else 0 \
    #     for line in str(docstring).splitlines()]
    # docstring_line = sum(non_blank_docline)
    
    # if code_line > 150: return False
    # if docstring_line > 50: return False
    # if len(output['code_tokens']) > 1000: return False
    # if len(output['code_tokens']) < 5: return False
    # if len(output['docstring_tokens']) < 5: return False
    # if len(output['docstring_tokens']) > 500: return False
    return True


def extract_docstring(docstring: str, parameter_list: Union[List, Dict], language: str) -> Dict[str, Any]:
    """Extract docstring into parameter docstring
        
    Args:
        docstring (str): Input docstring
        parameter_list (List or Dict): List of parameter's name or Dict of name and its type
        language (str): Language
    
    Return:
        Dict[str, Any]: metadata of docstring
    """
    assert isinstance(language, str)
    assert isinstance(docstring, str)
    assert _DOCSTRING_PARSER_AVAILABLE == True, "`docstring_parser` is not install, try install from https://github.com/nmd-2000/docstring_parser"
    # assert type(parameter_list) in [List, Dict]
    
    # Checking
    if docstring == '' or docstring is None:
        return None
    
    language = str(language).lower()
    if language == 'c#':
        language = 'c_sharp'
    elif language == 'c++':
        language = 'cpp'
    assert language in SUPPORTED_LANGUAGE, f'Expect {language} in {SUPPORTED_LANGUAGE}'
    
    # Setup
    metadata = {
        'docstring': '',
        'docstring_params': {
            'returns': [],
            'raises': [],
            'params': [],
            'outlier_params': [],
            'others': []
        },
    }
    params_dict = {}
    outlier_params_dict = {}
    
    type_flag = False
    if isinstance(parameter_list, List):
        for each in parameter_list:
            params_dict[each] = {'identifier': each, 'docstring': None, 'docstring_tokens': []}
            # metadata['docstring_params'][each] = {'docstring': None, 'docstring_tokens': []}
    elif isinstance(parameter_list, Dict):
        type_flag = True
        for key, val in parameter_list.items():
            params_dict[key] = {'identifier': key, 'docstring': None, 'type': val, 'docstring_tokens': []}
            # metadata['docstring_params'][key] = {'docstring': None, 'type': val, 'docstring_tokens': []}
    
    # Extract docstring
    docstring_style_list = STYLE_MAP[language]
    rets = []
    
    try:
        for style in docstring_style_list:
            try:
                ret = parse(docstring, style)
                # break
            except ParseError:
                pass
            else:
                rets.append(ret)
    except Exception:
        return None
    extract_docstring = sorted(rets, key=lambda d: len(d.meta), reverse=True)
    
    if len(extract_docstring) < 1:
        return None  # unable to parse
    extract_docstring = extract_docstring[0]
    
    assert isinstance(extract_docstring, Docstring)
    
    new_docstring = ''
    if extract_docstring.short_description != None:
        new_docstring += extract_docstring.short_description
    if extract_docstring.long_description != None:
        new_docstring += '\n' + extract_docstring.long_description
        
    # change clean_comment -> clean_docstring
    short_docstring = get_first_sentence(new_docstring)
    new_docstring = clean_docstring(new_docstring)
    metadata['short_docstring'] = short_docstring
    metadata['docstring'] = new_docstring
    metadata['short_docstring_tokens'] = tokenize_docstring(short_docstring)
    metadata['docstring_tokens'] = tokenize_docstring(new_docstring)
    
    visited = []
    for param in extract_docstring.params:
        visited.append(param)
        param_identifier = param.arg_name
        param_type = param.type_name
        param_default = param.default
        param_is_optional = param.is_optional
        # change clean_comment -> clean docstring
        param_docstring = clean_docstring(param.description, loosen_filter=True)
        param_token = tokenize_docstring(param_docstring)
        
        param_metadata = {
            'identifier': param_identifier,
            'docstring': param_docstring,
            'docstring_tokens': param_token,
            'default': param_default,
            'is_optional': param_is_optional,
        }

        if not type_flag:
            param_metadata['type'] = param_type
            if param_identifier in parameter_list:
                params_dict[param_identifier].update(param_metadata)
                # metadata['docstring_params'][param_identifier] = param_metadata
            else:
                outlier_params_dict[param_identifier] = param_metadata
                # metadata['docstring_params']['other_params'][param_identifier] = param_metadata
        else:    
            if param_identifier in parameter_list.keys():
                params_dict[param_identifier].update(param_metadata)
                # metadata['docstring_params'][param_identifier] = param_metadata
            else:
                outlier_params_dict[param_identifier] = param_metadata
                # metadata['docstring_params']['other_params'][param_identifier] = param_metadata
    
    for key, val in params_dict.items():
        metadata['docstring_params']['params'].append(val)
    for key, val in outlier_params_dict.items():
        metadata['docstring_params']['outlier_params'].append(val)


    for retun in extract_docstring.many_returns:
        visited.append(retun)
        return_docstring = clean_docstring(retun.description, loosen_filter=True)
        return_tokens = tokenize_docstring(return_docstring)
        return_type = retun.type_name
        
        return_metadata = {
            'docstring': return_docstring,
            'docstring_tokens': return_tokens,
            'type': return_type,
        }
        
        metadata['docstring_params']['returns'].append(return_metadata)
    
    for raiser in extract_docstring.raises:
        visited.append(raiser)
        raise_docstring = clean_docstring(raiser.description, loosen_filter=True)
        raise_tokens = tokenize_docstring(raise_docstring)
        raise_type = raiser.type_name
        
        raise_metadata = {
            'docstring': raise_docstring,
            'docstring_tokens': raise_tokens,
            'type': raise_type,
        }
        
        metadata['docstring_params']['raises'].append(raise_metadata)
        
    for item in extract_docstring.meta:
        if item not in visited:
            try:
                item_docs = clean_docstring(item.description, loosen_filter=True)
                metadata['docstring_params']['others'].append({
                    'identifier': item.args[0],
                    'docstring': item_docs,
                    'docstring_tokens': tokenize_docstring(item_docs),
                })
            except Exception:
                # Let it go ...
                pass
    
    return metadata


def write_jsonl(data, save_path: str):
    with open(save_path, "a") as file:
        for item in data:
            json.dump(item, file, ensure_ascii=False)
            file.write('\n')


if __name__ == '__main__':
    # lang_list = ['python', 'cpp', 'java', 'c-sharp', 'ruby', 'rust', 'javascript', 'php', 'go']
    
    # for lang in lang_list:
    #     build_language(lang)
    build_language('rust')

    