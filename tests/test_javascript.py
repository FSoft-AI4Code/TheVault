'''test for JavaScript parser'''
import os
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
from src.utils.parser import JavascriptParser
from src.utils import parse_code

ROOT_PATH = str(Path(__file__).parents[1])

class Test_JavascriptParser(unittest.TestCase):
    def setUp(self) -> None:
        with open('tests/test_sample/javascript_test_sample.js', 'r') as file:
            self.code_sample = file.read()
            
        tree = parse_code(self.code_sample, 'javascript')
        self.root_node = tree.root_node

        return super().setUp()

    def test_get_function_list(self):
        root = self.root_node
        
        function_list = JavascriptParser.get_function_list(root)
        
        self.assertEqual(len(function_list), 7)

    def test_get_class_list(self):
        root = self.root_node
        
        class_list = JavascriptParser.get_class_list(root)
        
        self.assertEqual(len(class_list), 2)

    def test_get_docstring(self):
        code_sample = """
        /**
        * Dispatched when the repositories are loaded by the request saga
        *
        * @param  {array} repos The repository data
        * @param  {string} username The current username
        *
        * @return {object}      An action object with a type of LOAD_REPOS_SUCCESS passing the repos
        */
        function songsLoaded(repos, username) {
            return {
                type: LOAD_SONGS_SUCCESS,
            repos,
            username,
            };
        }
        
        class Car {
            /**
            * Present the object Car
            *
            * @return {None}
            */
            present() {
                return 'I have a ' + this.carname;
            }
        }
        """

        tree = parse_code(code_sample, 'javascript')
        root = tree.root_node
        
        fn1, fn2 = JavascriptParser.get_function_list(root)
        

        docs1 = JavascriptParser.get_docstring(fn1, code_sample)
        docs2 = JavascriptParser.get_docstring(fn2, code_sample)
        
        self.assertEqual(docs1, '\nDispatched when the repositories are loaded by the request saga\n\n@param  {array} repos The repository data\n@param  {string} username The current username\n\n@return {object}      An action object with a type of LOAD_REPOS_SUCCESS passing the repos\n')
        self.assertEqual(docs2, '\nPresent the object Car\n\n@return {None}\n')

    def test_get_function_metadata(self):
        root = self.root_node
        
        function = JavascriptParser.get_function_list(root)[1]
        metadata = JavascriptParser.get_function_metadata(function, self.code_sample)

        self.assertEqual(metadata['identifier'], 'songsLoaded')
        self.assertEqual(metadata['parameters'], ['repos', 'username'])

    def test_get_class_metadata(self):
        root = self.root_node
        
        classes = JavascriptParser.get_class_list(root)[0]
        metadata = JavascriptParser.get_class_metadata(classes, self.code_sample)

        self.assertEqual(metadata['identifier'], 'Model')
        self.assertEqual(metadata['parameters'], ['Car'])

    def test_extract_docstring(self):
        pass
        

if __name__ == '__main__':
    unittest.main()
