import re
from typing import List, Dict, Any

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import if_comment_generated, clean_comment, strip_c_style_comment_delimiters


class JavaParser(LanguageParser):

    FILTER_PATHS = ('test', 'tests')

    BLACKLISTED_FUNCTION_NAMES = ['toString', 'hashCode', 'equals', 'finalize', 'notify', 'notifyAll', 'clone']

    @staticmethod
    def get_docstring_node(node):
        """
        Get docstring node from it parent node. Expect return list have length==1
        
        Args:
            node (tree_sitter.Node): parent node (usually function node) to get its docstring
        Return:
            List: list of docstring nodes
        """
        docstring_node = []
        
        if node.prev_sibling:
            prev_node = node.prev_sibling
            if prev_node.type == 'block_comment' or prev_node.type == 'line_comment':
                docstring_node.append(prev_node)
        
        return docstring_node

    @staticmethod
    def get_docstring(node, blob):
        """
        Get docstring description for node
        
        Args:
            node (tree_sitter.Node)
            blob (str): original source code which parse the `node`
        Returns:
            str: docstring
        """
        docstring_node = JavaParser.get_docstring_node(node)

        docstring = ''
        if docstring_node:
            docstring = match_from_span(docstring_node[0], blob)
        return docstring

    @staticmethod
    def get_comment_node(function_node):
        """
        Return all comment node inside a parent node
        Args:
            node (tree_sitter.Node)
        Return:
            List: list of comment nodes
        """
        comment_node = []
        traverse_type(function_node, comment_node, kind=['line_comment'])
        return comment_node
    
    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class_declaration'])
        return res
    
    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['method_declaration'])
        return res
    
    @staticmethod
    def is_method_body_empty(node):
        for c in node.children:
            if c.type in {'method_body', 'constructor_body'}:
                if c.start_point[0] == c.end_point[0]:
                    return True
    
    @staticmethod
    def get_class_metadata(class_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        argument_list = []
        for child in class_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'superclass' or child.type == 'super_interfaces':
                for subchild in child.children:
                    if subchild.type == 'type_list' or subchild.type == 'type_identifier':
                        argument_list.append(match_from_span(subchild, blob))
                    
        metadata['parameters'] = argument_list
        return metadata

    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
            'type': ''
        }
        
        params = {}
        for child in function_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'type_identifier':
                metadata['type'] = match_from_span(child, blob)
            elif child.type == 'formal_parameters':
                param_list = []
                traverse_type(child, param_list, ['formal_parameter'])
                for param in param_list:
                    param_type = match_from_span(param.child_by_field_name('type'), blob)
                    identifier = match_from_span(param.child_by_field_name('name'), blob)
                    params[identifier] = param_type
        
        metadata['parameters'] = params
        return metadata
