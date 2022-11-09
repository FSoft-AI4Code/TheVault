from typing import List, Dict, Any, Optional, Iterator

import tree_sitter

from src.utils.noise_detection import clean_comment, strip_c_style_comment_delimiters
from src.utils.parser.language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
# from function_parser.parsers.commentutils import get_docstring_summary, strip_c_style_comment_delimiters

import re

from docstring_parser import parse
from docstring_parser.common import *


CPP_STYLE_MAP = [
    # DocstringStyle.REST,
    # DocstringStyle.GOOGLE,
    # DocstringStyle.NUMPYDOC,
    # DocstringStyle.EPYDOC,
]

class CppParser(LanguageParser):
    @staticmethod
    def get_docstring(node, blob):
        docstring_node = []
        
        prev_node = node.prev_sibling
        while prev_node is not None and prev_node.type == 'comment':
            docstring_node.insert(0, prev_node)
            prev_node = prev_node.prev_sibling
            
            # else:
            #     break
        
        docstring = '\n'.join((strip_c_style_comment_delimiters(match_from_span(s, blob)) for s in docstring_node))
        return docstring
    
    @staticmethod
    def get_comment_node(node):
        comment_node = []
        traverse_type(node, comment_node, kind=['comment'])
        return comment_node
    
    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, Any]:
        """
        Function metadata contains:
            - identifier (str): function name
            - parameters (Dict[str, str]): parameter's name and their type (e.g: {'param_a': 'int'})
            - type (str): return type
        """
        metadata = {
            'identifier': '',
            'parameters': {},
            'type': ''
        }
        assert type(function_node) == tree_sitter.Node
        
        for child in function_node.children:
            if child.type == 'primitive_type':
                metadata['type'] = match_from_span(child, blob)
            elif child.type == 'function_declarator':
                for subchild in child.children:
                    if subchild.type in ['qualified_identifier', 'identifier']:
                        metadata['identifier'] = match_from_span(subchild, blob)
                    elif subchild.type == 'parameter_list':
                        param_nodes = []
                        traverse_type(subchild, param_nodes, ['parameter_declaration'])
                        for param in param_nodes:
                            param_type = match_from_span(param.children[0], blob)
                            param_identifier = match_from_span(param.children[1], blob)
                            
                            metadata['parameters'][param_identifier] = param_type

        return metadata

    @staticmethod
    def get_class_metadata(class_node, blob: str) -> Dict[str, str]:
        """
        Class metadata contains:
            - identifier (str): class's name
            - argument_list (List[str]): inheritance class
        """
        metadata = {
            'identifier': '',
            'argument_list': '',
        }
        assert type(class_node) == tree_sitter.Node
        
        for child in class_node.children:
            if child.type == 'type_identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'base_class_clause':
                argument_list = []
                for param in child.children:
                    if param.type == 'type_identifier':
                        argument_list.append(match_from_span(param, blob))
                metadata['argument_list'] = argument_list

        return metadata

    @staticmethod
    def is_function_empty(function_node) -> bool:
        pass

    @staticmethod
    def get_function_definitions(tree, blob: str, func_identifier_scope: Optional[str]=None) -> Iterator[Dict[str, Any]]:
        function_list = CppParser.get_function_list(tree.root_node)
        for function_node in function_list:
            if CppParser.is_function_empty(function_node):
                continue
            function_metadata = CppParser.get_function_metadata(function_node, blob)
            if func_identifier_scope is not None:
                # identifier is function name
                function_metadata['identifier'] = '{}.{}'.format(func_identifier_scope,
                                                                 function_metadata['identifier'])
                if function_metadata['identifier'].startswith('__') and function_metadata['identifier'].endswith('__'):
                    continue  # Blacklist built-in functions

            docstring_node = CppParser.get_docstring_node(function_node)
            comment_node = CppParser.get_comment_node(function_node)
            docstring = CppParser.process_docstring(docstring_node, blob)
            _docs = docstring
            try:
                docstring, param = CppParser.extract_docstring(docstring, function_metadata['parameters'])
            except:
                continue
            
            docstring = clean_comment(docstring, blob)
            _comment = [CppParser.process_docstring(cmt, blob) for cmt in comment_node]
            comment = [clean_comment(cmt) for cmt in _comment]
            if docstring == None:  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
                continue
            
            if if_comment_generated(function_metadata['identifier'], docstring):  # Auto code generation
                continue
            
            function_metadata['original_docstring'] = _docs
            function_metadata['docstring'] = docstring
            function_metadata['comment'] = comment
            function_metadata['docstring_tokens'] = tokenize_docstring(function_metadata['docstring'])
            function_metadata['docstring_param'] = param
            
            function_metadata['function'] = match_from_span(function_node, blob)
            exclude_node = [docstring_node] + comment_node
            function_metadata['function_tokens'] = tokenize_code(function_node, blob, exclude_node)
            # function_metadata['start_point'] = function_node.start_point
            # function_metadata['end_point'] = function_node.end_point

            yield function_metadata
            
    @staticmethod
    def get_class_definitions(tree, blob: str) -> Iterator[Dict[str, Any]]:
        classes_list = CppParser.get_class_list(tree.root_node)
        for class_node in classes_list:
            # filter 
            class_metadata = CppParser.get_class_metadata(class_node, blob)
            
            docstring_node = CppParser.get_docstring_node(class_node)
            docstring = CppParser.process_docstring(docstring_node, blob)
            comment_node = CppParser.get_comment_node(class_node)
            _docs = docstring
            try:
                docstring, param = CppParser.extract_docstring(docstring, class_metadata['argument_list'])
            except:
                continue
            
            docstring = clean_comment(docstring, blob)
            _comment = [CppParser.process_docstring(cmt, blob) for cmt in comment_node]
            # comment = [clean_comment(cmt) for cmt in _comment]
            
            if docstring == None:  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
                continue
            
            if if_comment_generated(class_metadata['identifier'], docstring):  # Auto code generation
                continue
            
            class_metadata['original_docstring'] = _docs
            class_metadata['docstring'] = docstring
            # class_metadata['comment'] = comment
            class_metadata['docstring_tokens'] = tokenize_docstring(class_metadata['docstring'])
            class_metadata['docstring_param'] = param
            
            class_metadata['class'] = match_from_span(class_node, blob)
            exclude_node = [docstring_node] + comment_node
            class_metadata['class_tokens'] = tokenize_code(class_node, blob, exclude_node)
            # class_metadata['start_point'] = function_node.start_point
            # class_metadata['end_point'] = function_node.end_point
            
            yield class_metadata
            
    @staticmethod
    def get_line_definitions(tree, blob: str):
        function_list = CppParser.get_function_list(tree.root_node)
        
        for function_node in function_list:
            comment_nodes = CppParser.get_comment_node(function_node)
            
            if not comment_nodes:
                continue
            
            comment_metadata = {
                'identifier': CppParser.get_function_metadata(function_node, blob)['identifier'],
                'function': match_from_span(function_node, blob),
                'function_tokens': tokenize_code(function_node, blob, comment_nodes),
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

    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['function_definition'])
        return res

    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class_specifier'])
        return res
