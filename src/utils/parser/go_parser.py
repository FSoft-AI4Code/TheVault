from typing import List, Dict, Any

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import clean_comment, strip_c_style_comment_delimiters
# from function_parser.parsers.commentutils import get_docstring_summary, strip_c_style_comment_delimiters


class GoParser(LanguageParser):

    FILTER_PATHS = ('test', 'vendor')
    
    @staticmethod
    def get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind='comment')
        return comment_node
    
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
    def get_docstring(node, blob):
        docstring_node = GoParser.get_docstring_node(node)
        docstring = '\n'.join((strip_c_style_comment_delimiters(match_from_span(s, blob)) for s in docstring_node))
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
                        identifier = match_from_span(subchild.child_by_field_name('name'), blob)
                        param_type = match_from_span(subchild.child_by_field_name('type'), blob)
                        
                        if identifier and param_type:
                            metadata['parameters'][identifier] = param_type
        
        return metadata

    @staticmethod
    def get_class_list(node):
        raise NotImplementedError()
    
    @staticmethod
    def get_class_metadata(class_node, blob) -> Dict[str, str]:
        raise UserWarning('Golang does not support class concept')

    @staticmethod
    def extract_docstring(docstring:str, parameter_list:Dict) -> List:
        if docstring == '':
            return None, None
        
        param = {'other_param': {}}
        for key, val in parameter_list.items():
            param[key] = {'docstring': None, 'type': val}
        
        return docstring, param
    
    @staticmethod
    def get_definition(tree, blob: str) -> List[Dict[str, Any]]:
        definitions = []
        comment_buffer = []
        for child in tree.root_node.children:
            if child.type == 'comment':
                comment_buffer.append(child)
            elif child.type in ('method_declaration', 'function_declaration'):
                
                docstring = '\n'.join([match_from_span(comment, blob) for comment in comment_buffer])
                docstring = strip_c_style_comment_delimiters(docstring)

                # docstring_summary = strip_c_style_comment_delimiters((get_docstring_summary(docstring)))

                metadata = GoParser.get_function_metadata(child, blob)
                
                _docs = docstring
                docstring, param = GoParser.extract_docstring(docstring, metadata['parameters'])
                comment_node = GoParser.__get_comment_node(child)
                docstring = clean_comment(docstring, blob)
                _comment = [strip_c_style_comment_delimiters(match_from_span(cmt, blob)) for cmt in comment_node]
                comment = [clean_comment(cmt) for cmt in _comment]
                
                definitions.append({
                    'type': child.type,
                    'identifier': metadata['identifier'],
                    'parameters': metadata['parameters'],
                    'function': match_from_span(child, blob),
                    'function_tokens': tokenize_code(child, blob),
                    'original_docstring': _docs,
                    'docstring': docstring,
                    'docstring_tokens': tokenize_docstring(docstring),
                    'docstring_param': param,
                    'comment': comment,
                    # 'docstring_summary': docstring_summary,
                    'start_point': child.start_point,
                    'end_point': child.end_point     
                })
                comment_buffer = []
            else:
                comment_buffer = []
        return definitions
