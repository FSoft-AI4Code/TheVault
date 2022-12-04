import re
from typing import List, Dict, Any

import tree_sitter

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
# from function_parser.parsers.commentutils import get_docstring_summary


class RubyParser(LanguageParser):

    FILTER_PATHS = ('test', 'vendor')

    BLACKLISTED_FUNCTION_NAMES = ['initialize', 'to_text', 'display', 'dup', 'clone', 'equal?', '==', '<=>',
                                  '===', '<=', '<', '>', '>=', 'between?', 'eql?', 'hash']

    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['method'])
        return res
    
    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class', 'module'])
        
        # remove class keywords
        for node in res[:]:
            if not node.children:
                res.remove(node)

        return res

    @staticmethod
    def get_docstring_node(node) -> str:
        docstring_node = []
        
        prev_node = node.prev_sibling        
        if not prev_node or prev_node.type != 'comment':
            parent_node = node.parent
            if parent_node:
                prev_node = parent_node.prev_sibling

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
    def get_docstring(node, blob):
        docstring_node = RubyParser.get_docstring_node(node)
        docstring = []
        for item in docstring_node:
            doc = match_from_span(item, blob)
            doc_lines = doc.split('\n')
            for line in doc_lines:
                if '=begin' in line or '=end' in line:
                    continue
                docstring.append(line)
            
        docstring = '\n'.join(docstring)
        return docstring
    
    @staticmethod
    def get_function_metadata(function_node, blob) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': [],
        }
        
        assert type(function_node) == tree_sitter.Node
        assert function_node.type == 'method'
        
        for child in function_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type in ['method_parameters', 'parameters', 'bare_parameters']:
                params = []
                traverse_type(child, params, ['identifier'])
                for item in params:
                    metadata['parameters'].append(match_from_span(item, blob))

        return metadata
    
    @staticmethod
    def get_class_metadata(class_node, blob):
        metadata = {
            'identifier': '',
            'parameters': [],
        }
        
        assert type(class_node) == tree_sitter.Node
        
        for child in class_node.children:
            if child.type == 'constant':
                metadata['identifier'] = match_from_span(child, blob)
            if child.type == 'superclass':
                for subchild in child.children:
                    if subchild.type == 'constant':
                        metadata['parameters'].append(match_from_span(subchild, blob))

        return metadata
        

    @staticmethod
    def get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind='comment')
        return comment_node
