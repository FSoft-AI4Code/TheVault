import re
from typing import List, Dict, Any
import tree_sitter

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import clean_comment, if_comment_generated, strip_c_style_comment_delimiters


class PhpParser(LanguageParser):

    FILTER_PATHS = ('test', 'tests')

    BLACKLISTED_FUNCTION_NAMES = ['__construct', '__destruct', '__call', '__callStatic',
                                  '__get', '__set', '__isset', '__unset',
                                  '__sleep', '__wakeup', '__toString', '__invoke',
                                  '__set_state', '__clone', '__debugInfo', '__serialize',
                                  '__unserialize']

    @staticmethod
    def get_docstring(node, blob: str) -> str:
        docstring_node = PhpParser.get_docstring_node(node)
        
        docstring = ''
        if docstring_node:
            docstring = match_from_span(docstring_node[0], blob)
            docstring = strip_c_style_comment_delimiters(docstring)
        
        return docstring
    
    @staticmethod
    def get_docstring_node(node):
        docstring_node = []
        
        if node.prev_sibling is not None:
            prev_node = node.prev_sibling
            if prev_node.type == 'comment':
                docstring_node.append(prev_node)
        
        return docstring_node
    
    @staticmethod
    def get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind='comment')
        return comment_node
    
    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class_declaration', 'trait_declaration'])
        return res
    
    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['function_definition', 'method_declaration'])
        return res
    
    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }

        params = []
        for n in function_node.children:
            if n.type == 'name':
                metadata['identifier'] = match_from_span(n, blob)
            if n.type == 'union_type':
                metadata['type'] = match_from_span(n, blob)
            elif n.type == 'formal_parameters':
                for param_node in n.children:
                    if param_node.type in ['simple_parameter', 'variadic_parameter', 'property_promotion_parameter']:
                        identifier = param_node.child_by_field_name('name')
                        name = match_from_span(identifier, blob)
                        if name.startswith('$'):
                            name = name[1:]
                        params.append(name)
                        
        metadata['parameters'] = params
        return metadata

    
    @staticmethod
    def get_class_metadata(class_node, blob):
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        assert type(class_node) == tree_sitter.Node
        
        for child in class_node.children:
            if child.type == 'name':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'base_clause':
                argument_list = []
                for param in child.children:
                    if param.type == 'name':
                        argument_list.append(match_from_span(param, blob))
                metadata['parameters'] = argument_list 
    
        return metadata
