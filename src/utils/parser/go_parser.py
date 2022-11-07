from typing import List, Dict, Any

from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import clean_comment, strip_c_style_comment_delimiters
# from function_parser.parsers.commentutils import get_docstring_summary, strip_c_style_comment_delimiters


class GoParser(LanguageParser):

    FILTER_PATHS = ('test', 'vendor')
    
    @staticmethod
    def __get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind='comment')
        return comment_node
    
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


    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        params = {}
        if function_node.type == 'function_declaration':
            metadata['identifier'] = match_from_span(function_node.children[1], blob)
            paramerter_list = match_from_span(function_node.children[2], blob).split(',')
        elif function_node.type == 'method_declaration':
            metadata['identifier'] = match_from_span(function_node.children[2], blob)
            paramerter_list = ','.join([match_from_span(function_node.children[1], blob),
                                        match_from_span(function_node.children[3], blob)]).split(',')

        for param in paramerter_list:
            item = param.strip('(').strip(')').split()
            if len(item) == 2:
                params[item[0].strip()] = item[1] # arg, type (no Optional)
            if len(item) == 1:
                params[item[0].strip()] = None

        metadata['parameters'] = params
        return metadata