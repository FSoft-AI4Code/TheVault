import re
from typing import List, Dict, Any

import tree_sitter

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type


class RustParser(LanguageParser):

    FILTER_PATHS = ('test', 'vendor')

    BLACKLISTED_FUNCTION_NAMES = ['main']

    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['function_item'])
        return res
    
    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['impl_item', 'mod_item'])  # trait is like an interface
        return res

    @staticmethod
    def get_docstring_node(node) -> str:
        docstring_node = []
        
        prev_node = node.prev_sibling
        if prev_node:
            if prev_node.type == 'block_comment':
                docstring_node.append(prev_node)
                
            elif prev_node.type == 'line_comment':
                docstring_node.append(prev_node)
                prev_node = prev_node.prev_sibling
                
                while prev_node and prev_node.type == 'line_comment':
                    # Assume the comment is dense
                    x_current = prev_node.start_point[0]
                    x_next = prev_node.next_sibling.start_point[0]
                    if x_next - x_current > 1:
                        break
                            
                    docstring_node.insert(0, prev_node)    
                    prev_node = prev_node.prev_sibling
            
        return docstring_node
    
    @staticmethod
    def get_docstring(node, blob):
        # TODO: strip c style comment
        docstring_node = RustParser.get_docstring_node(node)
        docstring = []
        if docstring_node:
            for item in docstring_node:
                doc = match_from_span(item, blob)
                docstring.append(doc)

        docstring = '\n'.join(docstring)
        return docstring
    
    @staticmethod
    def get_function_metadata(function_node, blob) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': {},
        }
        
        assert type(function_node) == tree_sitter.Node
        assert function_node.type == 'function_item'
        
        for child in function_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type in ['parameters']:
                params = []
                traverse_type(child, params, ['parameter', 'self_parameter'])
                for item in params:
                    if item.type == 'self_parameter':
                        metadata['parameters'][match_from_span(item, blob)] = ''
                        continue    
                    
                    param_name = ''
                    param_type = item.child_by_field_name('type')
                    
                    if param_type:
                        param_type = match_from_span(param_type, blob)
                    else:
                        param_type = ''

                    for subchild in item.children:
                        if subchild.type  == 'identifier':
                            param_name = match_from_span(subchild, blob)

                    if param_name:
                        metadata['parameters'][param_name] = param_type

        return metadata
    
    @staticmethod
    def get_class_metadata(class_node, blob):
        metadata = {
            'identifier': '',
            'parameters': [],
        }
        
        assert type(class_node) == tree_sitter.Node
        
        if class_node.type == 'mod_item':
            for child in class_node.children:
                if child.type ==  'identifier':
                    metadata['identifier'] = match_from_span(child, blob)
        
        else:
            identifier = []
            traverse_type(class_node, identifier, ['type_identifier'])
            
            metadata['identifier'] = match_from_span(identifier[0], blob)
            if len(identifier) > 1:
                for param in identifier[1:]:
                    metadata['parameters'].append(match_from_span(param, blob))

        return metadata
        

    @staticmethod
    def get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind='comment')
        return comment_node
