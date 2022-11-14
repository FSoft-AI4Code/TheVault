from typing import List, Dict, Any

import tree_sitter

from src.utils.noise_detection import strip_c_style_comment_delimiters
from src.utils.parser.language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type

from docstring_parser import parse
from docstring_parser.common import *


CPP_STYLE_MAP = [
    DocstringStyle.JAVADOC,
]

class CppParser(LanguageParser):
    
    BLACKLISTED_FUNCTION_NAMES = ['main', 'constructor']
    
    @staticmethod
    def get_docstring(node, blob):
        docstring_node = CppParser.get_docstring_node(node)
        docstring = '\n'.join((strip_c_style_comment_delimiters(match_from_span(s, blob)) for s in docstring_node))
        return docstring
    
    @staticmethod
    def get_docstring_node(node):
        docstring_node = []
        
        prev_node = node.prev_sibling
        if prev_node and prev_node.type == 'comment':
            docstring_node.append(prev_node)
            prev_node = prev_node.prev_sibling

        while prev_node and prev_node.type == 'comment':
            # Assume the comment is dense
            x_current = prev_node.start_point[0]
            x_next = prev_node.next_sibling.start_point[0]
            if x_next - x_current > 1:
                break
            
            docstring_node.insert(0, prev_node)    
            prev_node = prev_node.prev_sibling
        
        return docstring_node
    
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
                            if len(param.children) < 2:
                                continue
                            param_type = match_from_span(param.children[0], blob)
                            param_identifier = match_from_span(param.children[1], blob)
                            
                            metadata['parameters'][param_identifier] = param_type

        return metadata

    @staticmethod
    def get_class_metadata(class_node, blob: str) -> Dict[str, str]:
        """
        Class metadata contains:
            - identifier (str): class's name
            - parameters (List[str]): inheritance class
        """
        metadata = {
            'identifier': '',
            'parameters': '',
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
                metadata['parameters'] = argument_list

        return metadata
