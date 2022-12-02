from typing import List, Dict, Any

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import clean_comment, strip_c_style_comment_delimiters
# from function_parser.parsers.commentutils import get_docstring_summary, strip_c_style_comment_delimiters


class GoParser(LanguageParser):

    BLACKLISTED_FUNCTION_NAMES = ['test', 'vendor']
    
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
        traverse_type(function_node, comment_node, kind='comment')
        return comment_node
    
    @staticmethod
    def get_docstring_node(node):
        """
        Get docstring node from it parent node.
        Go's docstring is written line by line
        
        Args:
            node (tree_sitter.Node): parent node (usually function node) to get its docstring
        Return:
            List: list of docstring nodes
        Example:
            str = '''
                // The path package should only be used for paths separated by forward
                // slashes, such as the paths in URLs. This package does not deal with
                // Windows paths with drive letters or backslashes; to manipulate
                // operating system paths, use the [path/filepath] package.
                func (e TypeError) Error() string {
                    ...
                }
            '''
            ...
            print(GoParser.get_docstring_node(function_node))
            
            >>> [<Node type=comment, start_point=(x, y), end_point=(x, y)>, \
                <Node type=comment, start_point=(x, y), end_point=(x, y)>, \
                <Node type=comment, start_point=(x, y), end_point=(x, y)>, \
                <Node type=comment, start_point=(x, y), end_point=(x, y)>]
        """
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
    def get_docstring(node, blob):
        """
        Get docstring description for node
        
        Args:
            node (tree_sitter.Node)
            blob (str): original source code which parse the `node`
        Returns:
            str: docstring
        """
        docstring_node = GoParser.get_docstring_node(node)
        docstring = '\n'.join(match_from_span(s, blob) for s in docstring_node)
        return docstring
    
    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['method_declaration', 'function_declaration'])
        return res
    
    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': {},
            'type': '',
        }
        
        for child in function_node.children:
            if child.type == 'field_identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'type_identifier':
                metadata['type'] = match_from_span(child, blob)
            elif child.type == 'parameter_list':
                for subchild in child.children:
                    if subchild.type in ['parameter_declaration', 'variadic_parameter_declaration']:
                        identifier_node = subchild.child_by_field_name('name')
                        param_type = match_from_span(subchild.child_by_field_name('type'), blob)
                        
                        if not identifier_node:
                            continue
                        
                        identifier = match_from_span(identifier_node, blob)
                        if identifier and param_type:
                            metadata['parameters'][identifier] = param_type
        
        return metadata

    @staticmethod
    def get_class_list(node):
        pass
    
    @staticmethod
    def get_class_metadata(class_node, blob) -> Dict[str, str]:
        pass
