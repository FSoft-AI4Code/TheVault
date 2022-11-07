import re
from typing import List, Dict, Any

from docstring_parser import parse, DocstringStyle
from docstring_parser.common import *
from .language_parser import LanguageParser, match_from_span, tokenize_code, tokenize_docstring, traverse_type
from ..noise_detection import if_comment_generated, clean_comment, strip_c_style_comment_delimiters


class JavaParser(LanguageParser):

    FILTER_PATHS = ('test', 'tests')

    BLACKLISTED_FUNCTION_NAMES = {'toString', 'hashCode', 'equals', 'finalize', 'notify', 'notifyAll', 'clone'}

    @staticmethod
    def __get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind=['line_comment'])
        return comment_node
    
    @staticmethod
    def extract_docstring(docstring:str, parameter_list:Dict[str, str]) -> List:
        if docstring == '':
            return None, None
        
        param = {'other_param': {}}
        for each in parameter_list.keys():
            param[each] = {'docstring': None}
            
        _docstring = parse(docstring, DocstringStyle.JAVADOC)
        
        for item in _docstring.meta:
            if len(item.args) > 0:
                tag = item.args[0]
                if tag in PARAM_KEYWORDS:
                    _param_name = item.arg_name
                    _param_default = item.default
                    _param_docstring = item.description
                    _param_optional = item.is_optional
                
                    if _param_name in param.keys():
                        param[_param_name]['docstring'] = _param_docstring
                        param[_param_name]['type'] = parameter_list[_param_name]
                        
                        if _param_default != None:
                            param[_param_name]['default'] = _param_type
                        if _param_optional != None:
                            param[_param_name]['default'] = True
                    
                    else:
                        param['other_param'][_param_name] = {}
                        param['other_param'][_param_name]['docstring'] = _param_docstring
                        
                        if _param_default != None:
                            param['other_param'][_param_name]['default'] = _param_type
                
                elif tag in RETURNS_KEYWORDS | RAISES_KEYWORDS | YIELDS_KEYWORDS:  # other tag (@raise, @return, ...)
                    _param_docstring = item.description
                    
                    if _param_docstring != None and _param_docstring != "None":
                        _p = {'docstring': _param_docstring}
        
                        try:
                            _param_type = item.type_name                            
                            if _param_type != None:
                                _p = {'docstring': _param_docstring, 'type': _param_type}
                        except Exception:
                            pass
                            
                        if tag in param.keys():
                            if isinstance(param[tag], Dict):
                                param[tag] = [param[tag], _p]
                            
                            elif isinstance(param[tag], List):
                                param[tag].append(_p)
                        else:
                            param[tag] = _p
                            
        new_docstring = ''
        if _docstring.short_description != None:
            new_docstring += _docstring.short_description + '\n'
        if _docstring.long_description != None:
            new_docstring += _docstring.long_description
        
        return new_docstring, param

    @staticmethod
    def get_definition(tree, blob: str) -> List[Dict[str, Any]]:
        classes = (node for node in tree.root_node.children if node.type == 'class_declaration')
        definitions = []
        for _class in classes:
            class_identifier = match_from_span([child for child in _class.children if child.type == 'identifier'][0], blob).strip()
            for child in (child for child in _class.children if child.type == 'class_body'):
                for idx, node in enumerate(child.children):
                    if node.type == 'method_declaration':
                        if JavaParser.is_method_body_empty(node):
                            continue
                        docstring = ''
                        if idx - 1 >= 0 and child.children[idx-1].type == 'block_comment':
                            if child.children[idx-1].type == 'block_comment':
                                docstring = match_from_span(child.children[idx - 1], blob)
                                docstring = strip_c_style_comment_delimiters(docstring)
                            
                            # else:
                            #     _idx = idx
                            #     _docstring = []
                            #     while (_idx >= 0):
                            #         if child.children[_idx-1].type == 'line_comment':
                            #             _docstring.insert(0, child.children[_idx-1])
                                        
                            #             # line = match_from_span(child.children[_idx - 1], blob)
                            #             # line = strip_c_style_comment_delimiters(line)
                            #         _idx -= 1
                                
                            #     docstring = ' /n'.join(_docstring)
                                
                        # docstring_summary = get_docstring_summary(docstring)

                        metadata = JavaParser.get_function_metadata(node, blob)
                        if metadata['identifier'] in JavaParser.BLACKLISTED_FUNCTION_NAMES:
                            continue
                        
                        _docs = docstring
                        comment_node = JavaParser.__get_comment_node(node)
                        docstring, param = JavaParser.extract_docstring(docstring, metadata['parameters'])
                        docstring = clean_comment(docstring, blob)
                        _comment = [strip_c_style_comment_delimiters(match_from_span(cmt, blob)) for cmt in comment_node]
                        comment = [clean_comment(cmt) for cmt in _comment]
                        if docstring == None or docstring == '':  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
                            continue
                        
                        if if_comment_generated(metadata['identifier'], docstring):  # Auto code generation
                            continue
                        
                        
                        definitions.append({
                            'type': node.type,
                            'identifier': '{}.{}'.format(class_identifier, metadata['identifier']),
                            'parameters': metadata['parameters'],
                            'function': match_from_span(node, blob),
                            'function_tokens': tokenize_code(node, blob),
                            'original_docstring': _docs,
                            'docstring': docstring,
                            'docstring_tokens': tokenize_docstring(docstring),
                            'docstring_param': param,
                            'comment': comment,
                            # 'docstring_summary': docstring_summary,
                            'start_point': node.start_point,
                            'end_point': node.end_point
                        })
        return definitions

    @staticmethod
    def get_class_metadata(class_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'argument_list': '',
        }
        is_header = False
        for n in class_node.children:
            if is_header:
                if n.type == 'identifier':
                    metadata['identifier'] = match_from_span(n, blob).strip('(:')
                elif n.type == 'argument_list':
                    metadata['argument_list'] = match_from_span(n, blob)
            if n.type == 'class':
                is_header = True
            elif n.type == ':':
                break
        return metadata

    @staticmethod
    def is_method_body_empty(node):
        for c in node.children:
            if c.type in {'method_body', 'constructor_body'}:
                if c.start_point[0] == c.end_point[0]:
                    return True

    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }

        declarators = []
        traverse_type(function_node, declarators, '{}_declaration'.format(function_node.type.split('_')[0]))
        params = {}
        for n in declarators[0].children:
            if n.type == 'identifier':
                metadata['identifier'] = match_from_span(n, blob).strip('(')
            elif n.type == 'formal_parameters':
                parameter_list = match_from_span(n, blob).split(',')
                for param in parameter_list:
                    item = param.strip('(').strip(')').split()
                    if len(item) > 0:
                        params[item[-1].strip()] = item[0]  # arg, type
        metadata['parameters'] = params
        return metadata
