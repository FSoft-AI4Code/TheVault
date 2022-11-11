from typing import List, Dict, Any

from docstring_parser import parse, DocstringStyle
from docstring_parser.common import *
from .language_parser import LanguageParser, match_from_span, nodes_are_equal, tokenize_code, tokenize_docstring, traverse_type, previous_sibling, \
    node_parent, traverse_type_parent
from ..noise_detection import if_comment_generated, clean_comment, strip_c_style_comment_delimiters


class JavascriptParser(LanguageParser):

    FILTER_PATHS = ('test', 'node_modules')

    BLACKLISTED_FUNCTION_NAMES = {'toString', 'toLocaleString', 'valueOf', 'constructor'}

    @staticmethod
    def get_docstring_node(node):
        docstring_node = []
        parent_node = node.parent
        
        if parent_node:
            if parent_node.type == 'class_body':  # node inside a class
                prev_node = node.prev_sibling
            else:
                prev_node = parent_node.prev_sibling

            if prev_node and prev_node.type == 'comment':
                docstring_node.append(prev_node)
            
        return docstring_node
    
    @staticmethod
    def get_docstring(node, blob):
        docstring_node = JavascriptParser.get_docstring_node(node)
        docstring = '\n'.join((strip_c_style_comment_delimiters(match_from_span(s, blob)) for s in docstring_node))
        return docstring
    
    @staticmethod
    def get_comment_node(function_node):
        comment_node = []
        traverse_type(function_node, comment_node, kind=['comment'])
        return comment_node
    
    @staticmethod
    def get_function_list(node):
        res = []
        traverse_type(node, res, ['function_declaration', 'method_definition'])
        return res
    
    @staticmethod
    def get_class_list(node):
        res = []
        traverse_type(node, res, ['class_declaration'])
        return res

    @staticmethod
    def get_function_metadata(function_node, blob: str) -> Dict[str, str]:
        metadata = {
            'identifier': '',
            'parameters': '',
        }
        param = []
        for child in function_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'formal_parameters':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param.append(match_from_span(subchild, blob))

        metadata['parameters'] = param
        return metadata

    @staticmethod
    def get_class_metadata(class_node, blob):
        metadata = {
            'identifier': '',
            'argument_list': '',
        }
        param = []
        for child in class_node.children:
            if child.type == 'identifier':
                metadata['identifier'] = match_from_span(child, blob)
            elif child.type == 'class_heritage':
                for subchild in child.children:
                    if subchild.type == 'identifier':
                        param.append(match_from_span(subchild, blob))
                        
        metadata['argument_list'] = param
        return metadata

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
