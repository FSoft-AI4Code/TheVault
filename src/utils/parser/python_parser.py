import re
from typing import List, Dict, Iterable, Optional, Iterator, Any

from docstring_parser import parse
from docstring_parser.common import *

from .language_parser import match_from_span, tokenize_code, tokenize_docstring, LanguageParser, traverse_type
from ..noise_detection import if_comment_generated, clean_comment


PYTHON_STYLE_MAP = [
    DocstringStyle.REST,
    DocstringStyle.GOOGLE,
    DocstringStyle.NUMPYDOC,
    DocstringStyle.EPYDOC,
]

class PythonParser(LanguageParser):
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
            return docstring_node[0].children[0]  # only take the first block

        return None
    
    @staticmethod
    def get_comment_node(node):
        comment_node = []
        traverse_type(node, comment_node, kind=['comment'])
        return comment_node

    @staticmethod
    def process_docstring(docstring_node, blob: str) -> str:
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
        
        rets = []
        for style in PYTHON_STYLE_MAP:
            try:
                ret = parse(docstring, style)
                # break
            except ParseError:
                pass
            else:
                rets.append(ret)
        
        _docstring = sorted(rets, key=lambda d: len(d.meta), reverse=True)[0]
        
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
            'argument_list': '',
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
                    metadata['argument_list'] = args
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
                    print(item.type)
                    if item.type == 'comment' or (item.type == 'expression_statement' and item.children[0].type == 'string'):
                        continue
                    elif item.type != 'pass_statement' and item.type != 'raise_statement':
                        return False
        return True
    
    @staticmethod
    def is_error_node(function_node) -> bool:
        error_node = []
        traverse_type(function_node, error_node, ['ERROR'])
        if len(error_node) > 0:
            return True
        else:
            return False

    @staticmethod
    def get_function_definitions(tree, blob: str, func_identifier_scope: Optional[str]=None) -> Iterator[Dict[str, Any]]:
        function_list = PythonParser.get_function_list(tree.root_node)
        for function_node in function_list:
            if PythonParser.is_function_empty(function_node):
                continue
            if PythonParser.is_error_node(function_node):
                continue

            function_metadata = PythonParser.get_function_metadata(function_node, blob)
            if func_identifier_scope is not None:
                # identifier is function name
                function_metadata['identifier'] = '{}.{}'.format(func_identifier_scope,
                                                                 function_metadata['identifier'])
                if function_metadata['identifier'].startswith('__') and function_metadata['identifier'].endswith('__'):
                    continue  # Blacklist built-in functions

            docstring_node = PythonParser.get_docstring_node(function_node)
            comment_node = PythonParser.get_comment_node(function_node)
            docstring = PythonParser.process_docstring(docstring_node, blob)
            _docs = docstring
            try:
                docstring, param = PythonParser.extract_docstring(docstring, function_metadata['parameters'])
            except:
                continue
            
            docstring = clean_comment(docstring, blob)
            _comment = [PythonParser.process_docstring(cmt, blob) for cmt in comment_node]
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
    def get_class_definitions(tree, blob: str) -> Iterator[Dict[str, Any]]:
        classes_list = PythonParser.get_class_list(tree.root_node)
        for class_node in classes_list:
            # filter 
            class_metadata = PythonParser.get_class_metadata(class_node, blob)
            
            docstring_node = PythonParser.get_docstring_node(class_node)
            docstring = PythonParser.process_docstring(docstring_node, blob)
            comment_node = PythonParser.get_comment_node(class_node)
            _docs = docstring
            try:
                docstring, param = PythonParser.extract_docstring(docstring, class_metadata['argument_list'])
            except:
                continue
            
            docstring = clean_comment(docstring, blob)
            _comment = [PythonParser.process_docstring(cmt, blob) for cmt in comment_node]
            # comment = [clean_comment(cmt) for cmt in _comment]
            
            if docstring == None:  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
                continue
            
            if if_comment_generated(class_metadata['identifier'], docstring):  # Auto code generation
                continue
            
            class_metadata['original_docstring'] = _docs
            class_metadata['docstring'] = docstring
            # class_metadata['comment'] = comment
            class_metadata['docstring_tokens'] = tokenize_docstring(class_metadata['docstring'])
            class_metadata['docstring_param'] = param
            
            class_metadata['class'] = match_from_span(class_node, blob)
            exclude_node = [docstring_node] + comment_node
            class_metadata['class_tokens'] = tokenize_code(class_node, blob, exclude_node)
            # class_metadata['start_point'] = function_node.start_point
            # class_metadata['end_point'] = function_node.end_point
            
            yield class_metadata
            
    @staticmethod
    def get_line_definitions(tree, blob: str):
        function_list = PythonParser.get_function_list(tree.root_node)
        comment_list = []
        
        for function_node in function_list:
            comment_nodes = PythonParser.get_comment_node(function_node)
            
            if not comment_nodes:
                continue
            
            docstring_node = PythonParser.get_docstring_node(function_node)
            exclude_node = [docstring_node] + comment_nodes
            comment_metadata = {
                'identifier': PythonParser.get_function_metadata(function_node, blob)['identifier'],
                'function': match_from_span(function_node, blob),
                'function_tokens': tokenize_code(function_node, blob, exclude_node),
            }
            
            fn_line_start = function_node.start_point[0]
                
            for comment_node in comment_nodes:
                _comment_metadata = comment_metadata.copy()
                
                comments = [match_from_span(comment_node, blob)]
                prev_node = comment_node.prev_sibling
                next_node = comment_node.next_sibling
                
                _comment_metadata['prev_context'] = None
                _comment_metadata['next_context'] = None
                _comment_metadata['start_point'] = list(comment_node.start_point) #[0] - fn_line_start, comment_node.start_point[1]]
                _comment_metadata['end_point'] = list(comment_node.end_point) #[0] - fn_line_start, comment_node.end_point[1]]
                
                if prev_node is not None:
                    while prev_node.type == 'comment':
                        comments.insert(0, match_from_span(prev_node, blob))
                        _comment_metadata['start_point'] = list(prev_node.start_point)
                        if prev_node.prev_sibling is None: 
                            break
                        prev_node = prev_node.prev_sibling

                    if not prev_node.type == ":":
                        _comment_metadata['prev_context'] = {
                            'code': prev_node.text.decode(),
                            'start_point': list(prev_node.start_point), #[0] - fn_line_start, prev_node.start_point[1]],
                            'end_point': list(prev_node.end_point) # - fn_line_start, prev_node.end_point[1]]
                        }
                
                if next_node is not None:
                    while next_node.type == 'comment':
                        comments.append(match_from_span(next_node, blob))
                        _comment_metadata['end_point'] = list(next_node.start_point)
                        if next_node.next_sibling is None:
                            break
                        next_node = next_node.next_sibling    
                        
                    if next_node.type == "block":
                        next_node = next_node.children[0] if len(next_node.children) > 0 else None
                        
                    _comment_metadata['next_context'] = {
                        'code': next_node.text.decode(),
                        'start_point': [next_node.start_point[0] - fn_line_start, next_node.start_point[1]],
                        'end_point': [next_node.end_point[0] - fn_line_start, next_node.end_point[1]],
                    }
                
                _comment_metadata['start_point'][0] -= fn_line_start
                _comment_metadata['end_point'][0] -= fn_line_start
                
                _cmt = '\n'.join(comments)
                comment = clean_comment(_cmt)
                if comment == None:
                    continue
                
                _comment_metadata['original_comment'] = _cmt
                _comment_metadata['comment'] = comment
                _comment_metadata['comment_tokens'] = tokenize_docstring(comment)
                
                yield _comment_metadata

    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['function_definition'])
        return res
    
        # for child in node.children:
        #     if child.type == 'function_definition':
        #         yield child
        #     elif child.type == 'decorated_definition':
        #         for c in child.children:
        #             if c.type == 'function_definition':
        #                 yield c

    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class_definition'])
        return res
