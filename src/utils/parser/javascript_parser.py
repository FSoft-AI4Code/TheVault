from typing import List, Dict, Any

from docstring_parser import parse, DocstringStyle
from docstring_parser.common import *
from .language_parser import LanguageParser, match_from_span, nodes_are_equal, tokenize_code, tokenize_docstring, traverse_type, previous_sibling, \
    node_parent, traverse_type_parent
from ..noise_detection import if_comment_generated, clean_comment, strip_c_style_comment_delimiters


class JavascriptParser(LanguageParser):

    FILTER_PATHS = ('test', 'node_modules')

    BLACKLISTED_FUNCTION_NAMES = {'toString', 'toLocaleString', 'valueOf'}

    @staticmethod
    def get_docstring(parent_node, tree, node, blob: str) -> str:
        docstring = ''

        if parent_node.type == 'variable_declarator':
            base_node = node_parent(tree, parent_node)  # Get the variable declaration
            parent_node = node_parent(tree, base_node)
        elif parent_node.type == 'pair':
            base_node = parent_node  # This is a common pattern where a function is assigned as a value to a dictionary.
            parent_node = node_parent(tree, base_node)
        else:
            base_node = node

        index = 0
        for i, node_at_i in enumerate(parent_node.children):
            if nodes_are_equal(base_node, node_at_i):
                index = i
                 
        prev_sibling = None
        if index > 0:   
            prev_sibling = parent_node.children[index-1]

        if prev_sibling is not None and prev_sibling.type == 'comment':
            all_prev_comment_nodes = [prev_sibling]
            if index > 1:
                prev_sibling = parent_node.children[index-2]
                i = index - 2
                while prev_sibling is not None and prev_sibling.type == 'comment':
                    all_prev_comment_nodes.append(prev_sibling)
                    last_comment_start_line = prev_sibling.start_point[0]
                    i -= 1
                    prev_sibling = parent_node.children[i]
                    if prev_sibling.end_point[0] + 1 < last_comment_start_line:
                        break  # if there is an empty line, stop expanding.

            docstring = ' '.join((strip_c_style_comment_delimiters(match_from_span(s, blob)) for s in all_prev_comment_nodes[::-1]))
        return docstring
    
    @staticmethod
    def __get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind=['comment'])
        return comment_node
    
    @staticmethod
    def extract_docstring(docstring:str, parameter_list:List) -> List:
        if docstring == '':
            return None, None
        
        param = {'other_param': {}}
        for each in parameter_list:
            param[each] = {'docstring': None}
            
        _docstring = parse(docstring, DocstringStyle.JSDOC)
        
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
                        param[_param_name]['docstring'] = _param_docstring if _param_docstring != '' else None
                        
                        if _param_type != None:
                            param[_param_name]['type'] = _param_type
                        if _param_default != None:
                            param[_param_name]['default'] = _param_default
                        if _param_optional != None:
                            param[_param_name]['default'] = True
                    
                    else:
                        param['other_param'][_param_name] = {}
                        param['other_param'][_param_name]['docstring'] = _param_docstring if _param_docstring != '' else None
                        
                        if _param_type != None:
                            param['other_param'][_param_name]['type'] = _param_type
                        if _param_default != None:
                            param['other_param'][_param_name]['default'] = _param_default
                
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
        # function_nodes = []
        # traverse_type(tree.root_node, function_nodes, 'function')
        
        functions = []
        function_nodes = traverse_type_parent(tree.root_node, 'function')
        
        for parent_node, function in function_nodes:
            if function.children is None or len(function.children) == 0:
                continue
            # parent_node = node_parent(tree, function)

            functions.append((parent_node.type, function, JavascriptParser.get_docstring(parent_node, tree, function, blob)))
            # functions.append((parent_node.type, function, JavascriptParser.get_docstring(tree, function, blob)))
        
        definitions = []
        for node_type, function_node, docstring in functions:
            if docstring == '': continue
            metadata = JavascriptParser.get_function_metadata(function_node, blob)
            # docstring_summary = get_docstring_summary(docstring)

            if metadata['identifier'] in JavascriptParser.BLACKLISTED_FUNCTION_NAMES:
                continue
            
            _docs = docstring
            comment_node = JavascriptParser.__get_comment_node(function_node)
            docstring, param = JavascriptParser.extract_docstring(docstring, metadata['parameters'])
            docstring = clean_comment(docstring, blob)
            _comment = [strip_c_style_comment_delimiters(match_from_span(cmt, blob)) for cmt in comment_node]
            comment = [clean_comment(cmt) for cmt in _comment]

            if docstring == None:  # Non-literal, Interrogation, UnderDevlop, auto code or no-docstring
                continue
            
            if if_comment_generated(metadata['identifier'], docstring):  # Auto code generation
                continue
            
            definitions.append({
                'type': node_type,
                'identifier': metadata['identifier'],
                'parameters': metadata['parameters'],
                'function': match_from_span(function_node, blob),
                'function_tokens': tokenize_code(function_node, blob),
                'original_docstring': _docs,
                'docstring': docstring,
                'docstring_tokens': tokenize_docstring(docstring),
                'docstring_param': param,
                'comment': comment,
                # 'docstring_summary': docstring_summary,
                'start_point': function_node.start_point,
                'end_point': function_node.end_point     
            })
        return definitions


    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        identifier_nodes = [child for child in function_node.children if child.type == 'identifier']
        formal_parameters_nodes = [child for child in function_node.children if child.type == 'formal_parameters']
        if identifier_nodes:
            metadata['identifier'] = match_from_span(identifier_nodes[0], blob)
        if formal_parameters_nodes:
            params = []
            parameter_list = match_from_span(formal_parameters_nodes[0], blob).split(',')
            for param in parameter_list:
                item = param.strip('(').strip(')')
                if '=' in item:
                    item = item.split('=')[0]
                if item != '':
                    params.append(item.strip())
            metadata['parameters'] = params
        return metadata