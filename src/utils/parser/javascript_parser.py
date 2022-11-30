from typing import List, Dict, Any

from .language_parser import LanguageParser, match_from_span, nodes_are_equal, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import if_comment_generated, clean_comment, strip_c_style_comment_delimiters


class JavascriptParser(LanguageParser):

    FILTER_PATHS = ('test', 'node_modules')

    BLACKLISTED_FUNCTION_NAMES = ['toString', 'toLocaleString', 'valueOf', 'constructor']

    @staticmethod
    def get_docstring_node(node):
        docstring_node = []
        prev_node = node.prev_sibling
        parent_node = node.parent
                
        if prev_node and prev_node.type == 'comment':
            docstring_node.append(prev_node)
        
        elif parent_node:
            if parent_node.type != 'class_body':  # node not inside a class
                prev_node = parent_node.prev_sibling
                if prev_node and prev_node.type == 'comment':
                    docstring_node.append(prev_node)
            
        return docstring_node
    
    @staticmethod
    def get_docstring(node, blob):
        docstring_node = JavascriptParser.get_docstring_node(node)
        
        docstring = ''
        if docstring_node:
            docstring = match_from_span(docstring_node[0], blob)
        return docstring
    
    @staticmethod
    def get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind=['comment'])
        return comment_node
    
    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['function_declaration', 'function', 'method_definition', 'generator_function_declaration'])
        for node in res[:]:
            if not node.children:
                res.remove(node)

        return res
    
    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class_declaration', 'class'])
        for node in res[:]:
            if not node.children:
                res.remove(node)

        return res

    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        param = []
        for child in function_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'formal_parameters':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param.append(match_from_span(subchild, blob))

        metadata['parameters'] = param
        return metadata

    @staticmethod
    def get_class_metadata(class_node, blob):
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        param = []
        for child in class_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'class_heritage':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param.append(match_from_span(subchild, blob))
                        
        metadata['parameters'] = param
        return metadata
