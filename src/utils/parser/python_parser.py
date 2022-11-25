import re
from typing import List, Dict, Iterable, Optional, Iterator, Any

from .language_parser import match_from_span, tokenize_code, tokenize_docstring, LanguageParser, traverse_type
from ..noise_detection import if_comment_generated, clean_comment


class PythonParser(LanguageParser):
    
    BLACKLISTED_FUNCTION_NAMES = ['__init__', '__name__', '__main__']
    
    @staticmethod
    def get_docstring(node, blob):
        docstring_node = PythonParser.get_docstring_node(node)
        
        docstring = ''
        if docstring_node is not None:
            docstring = match_from_span(docstring_node[0], blob)
            docstring = docstring.strip('"').strip("'").strip("#")
        return docstring
    
    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['function_definition'])
        return res

    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class_definition'])
        return res
    
    @staticmethod
    def get_docstring_node(node):
        docstring_node = []
        # traverse_type(node, docstring_node, kind=['expression_statement']) #, 'comment'])
        for child in node.children:
            if child.type == 'block':
                for sub_child in child.children:
                    if sub_child.type == 'expression_statement':
                        docstring_node.append(sub_child)

        docstring_node = [node for node in docstring_node if
                          node.type == 'expression_statement' and node.children[0].type == 'string']
        
        if len(docstring_node) > 0:
            return [docstring_node[0].children[0]]  # only take the first block

        return None
    
    @staticmethod
    def get_comment_node(node):
        comment_node = []
        traverse_type(node, comment_node, kind=['comment'])
        return comment_node
    
    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
            'return': ''
        }

        is_header = False
        for child in function_node.children:
            if is_header:
                if child.type == 'identifier':
                    metadata['identifier'] = match_from_span(child, blob)
                elif child.type == 'parameters':
                    params = []
                    parameter_list = match_from_span(child, blob).split(',')  # self, param: str = None -> ['self', 'param: str = None']
                    for param in parameter_list:
                        item = re.sub(r'[^a-zA-Z0-9\_]', ' ', param).split()
                        if len(item) > 0:
                            params.append(item[0].strip())
                    metadata['parameters'] = params
            if child.type == 'def':
                is_header = True
            elif child.type == ':':
                is_header = False
            elif child.type == 'return_statement':
                metadata['return'] = match_from_span(child, blob)
        return metadata

    @staticmethod
    def get_class_metadata(class_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        is_header = False
        for child in class_node.children:
            if is_header:
                if child.type == 'identifier':
                    metadata['identifier'] = match_from_span(child, blob)
                elif child.type == 'argument_list':
                    args = []
                    argument_list = match_from_span(child, blob).split(',')
                    for arg in argument_list:
                        item = re.sub(r'[^a-zA-Z0-9\_]', ' ', arg).split()
                        if len(item) > 0:
                            args.append(item[0].strip())
                    metadata['parameters'] = args
            if child.type == 'class':
                is_header = True
            elif child.type == ':':
                break

        # get __init__ function
        return metadata

    @staticmethod
    def is_function_empty(function_node) -> bool:
        for child in function_node.children:
            if child.type == 'block':
                for item in child.children:
                    if item.type == 'comment' or (item.type == 'expression_statement' and item.children[0].type == 'string'):
                        continue
                    elif item.type != 'pass_statement' and item.type != 'raise_statement':
                        return False
        return True
