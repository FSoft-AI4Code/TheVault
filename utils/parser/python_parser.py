import re
from typing import List, Dict, Iterable, Optional, Iterator, Any

from docstring_parser import parse
from docstring_parser.common import *

from .language_parser import match_from_span, tokenize_code, tokenize_docstring, LanguageParser, traverse_type
from ..noise_detection import if_comment_generated, clean_comment

class PythonParser(LanguageParser):
    @staticmethod
    def __get_docstring_node(function_node):
        docstring_node = []
        traverse_type(function_node, docstring_node, kind=['expression_statement']) #, 'comment'])
        docstring_node = [node for node in docstring_node if
                          node.type == 'expression_statement' and node.children[0].type == 'string']
        
        # get block comment and line comment
        # docstring_node = [node for node in docstring_node \
        #     if (node.type == 'expression_statement' and node.children[0].type == 'string' ) \
        #     or node.type == 'comment']
        
        if len(docstring_node) > 0:
            # for node in docstring_node[:]:
            #     if node.type == 'expression_statement':
            #         docstring_node.remove(node)
            #         docstring_node.append(node.children[0])
            return docstring_node[0].children[0]
            # return docstring_node
        return None
    
    
    @staticmethod
    def __get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind=['comment'])
        return comment_node

    @staticmethod
    def get_docstring(docstring_node, blob: str) -> str:
        docstring = ''
        if docstring_node is not None:
            docstring = match_from_span(docstring_node, blob)
            docstring = docstring.strip('"').strip("'").strip("#")
        return docstring
    
    @staticmethod
    def extract_docstring(docstring: str, parameter_list: List) -> List:
        """Extract docstring into parameter docstring
        
        For example: 
            >>> extract_docstring('''Docstring
                
                :param a: docstring_a
                :type a: int
                :return: 2 power of a
                :rtype: int
                ''')
            
            
            ["Docstring",
            {  
                "a": {"docstring": "docstring_a, "type": "int"}
                "return": {"docstring": "2 power of a", "type": "int"}
            }]
        """
        if docstring == '':
            return None, None
        param = {'other_param': {}}
        for each in parameter_list:
            param[each] = {'docstring': None}
            
        _docstring = parse(docstring)
        
        for item in _docstring.meta:
            if len(item.args) > 0:
                tag = item.args[0]
                if tag in PARAM_KEYWORDS:
                    _param_name = item.arg_name
                    _param_type = item.type_name
                    _param_default = item.default
                    _param_docstring = item.description
                    _param_optional = item.is_optional
                
                    if _param_name in param.keys():
                        param[_param_name]['docstring'] = _param_docstring
                        
                        if _param_type != None:
                            param[_param_name]['type'] = _param_type
                        if _param_default != None:
                            param[_param_name]['default'] = _param_default
                        if _param_optional != None:
                            param[_param_name]['is_optional'] = True
                    
                    else:
                        param['other_param'][_param_name] = {}
                        param['other_param'][_param_name]['docstring'] = _param_docstring
                        if _param_type != None:
                            param['other_param'][_param_name]['type'] = _param_type
                        if _param_default != None:
                            param['other_param'][_param_name]['default'] = _param_default
                        if _param_optional != None:
                            param['other_param'][_param_name]['is_optional'] = True
                
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
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
            'return_statement': ''}

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
                metadata['return_statement'] = match_from_span(child, blob)
        return metadata

    @staticmethod
    def get_class_metadata(class_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'argument_list': '',
        }
        is_header = False
        for child in class_node.children:
            if is_header:
                if child.type == 'identifier':
                    metadata['identifier'] = match_from_span(child, blob)
                elif child.type == 'argument_list':
                    metadata['argument_list'] = match_from_span(child, blob)
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
                    if item.type != 'pass_statement' and item.type != 'raise_statement':
                        return False
        return True

    @staticmethod
    def get_definition(tree, blob: str, func_identifier_scope: Optional[str]=None) -> Iterator[Dict[str, Any]]:
        function_list = PythonParser.get_function_definitions(tree.root_node)
        for function_node in function_list:
            if PythonParser.is_function_empty(function_node):
                continue
            function_metadata = PythonParser.get_function_metadata(function_node, blob)
            if func_identifier_scope is not None:
                # identifier is function name
                function_metadata['identifier'] = '{}.{}'.format(func_identifier_scope,
                                                                 function_metadata['identifier'])
                if function_metadata['identifier'].startswith('__') and function_metadata['identifier'].endswith('__'):
                    continue  # Blacklist built-in functions

            docstring_node = PythonParser.__get_docstring_node(function_node)
            comment_node = PythonParser.__get_comment_node(function_node)
            docstring = PythonParser.get_docstring(docstring_node, blob)
            _docs = docstring
            docstring, param = PythonParser.extract_docstring(docstring, function_metadata['parameters'])
            
            docstring = clean_comment(docstring, blob)
            _comment = [PythonParser.get_docstring(cmt, blob) for cmt in comment_node]
            comment = [clean_comment(cmt) for cmt in _comment]
            if docstring == None:  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
                continue
            
            if if_comment_generated(function_metadata['identifier'], docstring):  # Auto code generation
                continue
            
            function_metadata['original_docstring'] = _docs
            function_metadata['docstring'] = docstring
            function_metadata['comment'] = comment
            function_metadata['docstring_tokens'] = tokenize_docstring(function_metadata['docstring'])
            function_metadata['docstring_param'] = param
            
            function_metadata['function'] = match_from_span(function_node, blob)
            exclude_node = [docstring_node] + comment_node
            function_metadata['function_tokens'] = tokenize_code(function_node, blob, exclude_node)
            # function_metadata['start_point'] = function_node.start_point
            # function_metadata['end_point'] = function_node.end_point

            yield function_metadata

    @staticmethod
    def get_function_definitions(node):
        for child in node.children:
            if child.type == 'function_definition':
                yield child
            elif child.type == 'decorated_definition':
                for c in child.children:
                    if c.type == 'function_definition':
                        yield c
