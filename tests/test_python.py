'''test for python parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import PythonParser

ROOT_PATH = str(Path(__file__).parents[1])

class Test_PythonParser(unittest.TestCase):
    def setUp(self) -> None:
        parser = Parser()
        py_language = Language(ROOT_PATH + "/tree-sitter/python.so", "python")
        parser.set_language(py_language)
        
        with open('tests/test_sample/py_test_sample.py', 'r') as file:
            self.code_sample = file.read()
        
        self.parser = parser
        return super().setUp()

    def test_get_function_list(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        function_list = PythonParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 3)

    def test_get_class_list(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        class_list = PythonParser.get_class_list(root)
        
        self.assertEqual(len(class_list), 1)
    
    def test_is_function_empty(self):
        code_sample = '''
        def test_sample():
            """This is a docstring"""
            # This function is empty
            pass
        '''
        tree = self.parser.parse(bytes(code_sample, 'utf8'))
        root = tree.root_node
        
        function = PythonParser.get_function_list(root)[0]
        
        is_empty = PythonParser.is_function_empty(function)
        self.assertEqual(is_empty, True)

    def test_get_docstring(self):
        code_sample = '''
        def test_sample():
            """This is a docstring"""
            return
        '''
        tree = self.parser.parse(bytes(code_sample, 'utf8'))
        root = tree.root_node
        
        function = PythonParser.get_function_list(root)[0]
        docstring = PythonParser.get_docstring(function, code_sample)
        self.assertEqual(docstring, "This is a docstring")

    def test_get_function_metadata(self):
        code_sample = '''
        def test_sample(arg1: str = "string", arg2 = "another_string"):
            return NotImplement()
        '''
        tree = self.parser.parse(bytes(code_sample, 'utf8'))
        root = tree.root_node
        
        function = list(PythonParser.get_function_list(root))[0]
        metadata = PythonParser.get_function_metadata(function, code_sample)

        self.assertEqual(metadata['parameters'], ['arg1', 'arg2'])
        self.assertEqual(metadata['identifier'], 'test_sample')

    def test_get_class_metadata(self):
        code_sample = '''
        class Sample(ABC):
            def __init__(self):
                pass

            def test_sample(self, arg1: str = "string", arg2 = "another_string"):
                return NotImplement()
        '''
        tree = self.parser.parse(bytes(code_sample, 'utf8'))
        root = tree.root_node
        
        classes = list(PythonParser.get_class_list(root))[0]
        metadata = PythonParser.get_class_metadata(classes, code_sample)

        self.assertEqual(metadata['parameters'], ['ABC'])
        self.assertEqual(metadata['identifier'], 'Sample')

    # def test_extract_docstring(self):
    #     # Test epydoc style ===================
    #     docstring = """
    #     This is a epydoc style.

    #     @param param1: this is a first param
    #     @param param2: this is a second param
    #     @param param3: this is a third param which not in function
    #     @return: this is a description of what is returned
    #     @raise keyError: raises an exception
    #     """
        
    #     parameter_list = ['param1', 'param2']
    #     new_docs, param = PythonParser.extract_docstring(docstring, parameter_list)
        
    #     self.assertEqual(new_docs, "This is a epydoc style.\n")
    #     self.assertTrue('return' in param.keys())
    #     self.assertTrue('raise' in param.keys())
        
    #     # Test reST style ===================
    #     del new_docs
    #     del param
    #     docstring = """
    #     This is a reST style.

    #     :param param1: this is a first param
    #     :param param2: this is a second param
    #     :param param3: this is a third param which not in function
    #     :returns: this is a description of what is returned
    #     :raises keyError: raises an exception
    #     """
        
    #     parameter_list = ['param1', 'param2']
    #     new_docs, param = PythonParser.extract_docstring(docstring, parameter_list)

    #     self.assertEqual(new_docs, "This is a reST style.\n")
    #     self.assertTrue('returns' in param.keys())
    #     self.assertTrue('raises' in param.keys())
        
    #     # Test google style ===================
    #     del new_docs
    #     del param
    #     docstring = """
    #     This is an example of Google style.

    #     Args:
    #         param1: This is the first param.
    #         param2: This is a second param.
    #         param3: This is a third param which not in function.

    #     Returns:
    #         This is a description of what is returned.

    #     Raises:
    #         KeyError: Raises an exception.
    #     """

        
    #     parameter_list = ['param1', 'param2']
    #     new_docs, param = PythonParser.extract_docstring(docstring, parameter_list)
        
    #     self.assertEqual(new_docs, "This is an example of Google style.\n")
    #     self.assertTrue('returns' in param.keys())
    #     self.assertTrue('raises' in param.keys())
        
    #     # Test numpy style ===================
    #     del new_docs
    #     del param
    #     docstring = """
    #     My numpydoc description of a kind
    #     of very exhautive numpydoc format docstring.

    #     Parameters
    #     ----------
    #     first : array_like
    #         the 1st param name `first`
    #     second :
    #         the 2nd param
    #     third : {'value', 'other'}, optional
    #         the 3rd param, by default 'value'

    #     Returns
    #     -------
    #     string
    #         a value in a string

    #     Raises
    #     ------
    #     KeyError
    #         when a key error
    #     OtherError
    #         when an other error
    #     """

        
    #     parameter_list = ['first', 'second']
    #     new_docs, param = PythonParser.extract_docstring(docstring, parameter_list)
        
    #     self.assertEqual(new_docs, "My numpydoc description of a kind\nof very exhautive numpydoc format docstring.")
    #     self.assertTrue('returns' in param.keys())
    #     self.assertTrue('raises' in param.keys())
        

if __name__ == '__main__':
    unittest.main()
