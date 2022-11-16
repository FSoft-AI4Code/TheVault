'''test for C# parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import CsharpParser
from src.utils import parse_code

ROOT_PATH = str(Path(__file__).parents[1])

class Test_CsharpParser(unittest.TestCase):
    def setUp(self) -> None:
        parser = Parser()
        language = Language(ROOT_PATH + "/tree-sitter/c_sharp.so", 'c_sharp')
        parser.set_language(language)
        
        with open('tests/test_sample/c_sharp_test_sample.cs', 'r') as file:
            self.code_sample = file.read()
        
        self.parser = parser
        return super().setUp()

    def test_get_function_list(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        function_list = CsharpParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 3)  # exclude constructor

    def test_get_class_list(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        class_list = CsharpParser.get_class_list(root)
        
        self.assertEqual(len(class_list), 1)

    def test_get_docstring(self):
        code_sample = """
        class Vehicle
        {
            public string brand = "Ford";  // Vehicle field
            
            // <summary>
            // Docstring of a method
            // </summary>
            // <param name="animal_honk">Argument.</param>
            // <returns>
            // None.
            public void honk(string animal_honk)
            {                    
                Console.WriteLine(animal_honk);
                Console.WriteLine("Tuut, tuut!");
            }
            
            /* Another method docstring
            in multiple line */
            public void _honk()
            {
                Console.WriteLine("Tuut, tuut!");
            }
        }   
        """
        tree = parse_code(code_sample, 'c_sharp')
        root = tree.root_node
        
        fn1, fn2 = list(CsharpParser.get_function_list(root))

        docs1 = CsharpParser.get_docstring(fn1, code_sample)
        docs2 = CsharpParser.get_docstring(fn2, code_sample)
        
        
        self.assertEqual(docs1, '<summary>\nDocstring of a method\n</summary>\n<param name="animal_honk">Argument.</param>\n<returns>\nNone.')
        self.assertEqual(docs2, 'Another method docstring\nin multiple line')
        

    def test_get_function_metadata(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        function = list(CsharpParser.get_function_list(root))[0]
        metadata = CsharpParser.get_function_metadata(function, self.code_sample)

        self.assertEqual(metadata['parameters'], {'path': 'string', 'filename': 'string'})
        self.assertEqual(metadata['identifier'], 'GetText')
        self.assertEqual(metadata['type'], 'string')

    def test_get_class_metadata(self):
        tree = self.parser.parse(bytes(self.code_sample, 'utf8'))
        root = tree.root_node
        
        classes = list(CsharpParser.get_class_list(root))[0]
        metadata = CsharpParser.get_class_metadata(classes, self.code_sample)

        self.assertEqual(metadata['parameters'], ['Animal'])
        self.assertEqual(metadata['identifier'], 'Dog')

    def test_extract_docstring(self):
        pass
        

if __name__ == '__main__':
    unittest.main()
