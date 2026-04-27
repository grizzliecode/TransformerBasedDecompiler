import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Query, QueryCursor
import os

class CParser:
    def __init__(self, file_path):
        if not os.path.exists(file_path):
            raise Exception(f"File specified by file_path does not exist {file_path}")
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
        self.file_path = file_path
        self.functions = {}
        self.ast = {}

    def _translate_ast(self, node, source_code):
        return source_code[node.start_byte:node.end_byte].decode("utf-8")

    def _extract_functions(self, root, source_code):
        query_text = """
        (function_definition
            declarator: (function_declarator
                declarator: (identifier) @function_name
            )
        ) @function_definition
        """
        query = Query(self.language, query_text)
        query_cursor = QueryCursor(query)
        captures = query_cursor.captures(root)
        names = captures.get('function_name', [])
        definitions = captures.get('function_definition', [])
        for name_node, def_node in zip(names, definitions):
            name_str = self._translate_ast(name_node, source_code)
            func_code = self._translate_ast(def_node, source_code)
            self.functions[name_str] = func_code
            self.ast[name_str] = str(def_node)
    

    def parse(self):
        source_code = ""
        with open(self.file_path, "r", encoding="utf-8", errors="replace") as fin:
            source_code_text = fin.read()
        source_code = source_code_text.encode("utf-8")
        try: 
            tree = self.parser.parse(source_code)
            self._extract_functions(tree.root_node, source_code)
        except Exception as e:
            print(f"Error parsing C file {self.file_path}: {e}")

    def get_function_by_name(self, name):
        return self.functions.get(name, None)
    
    def get_all_functions(self):
        return self.functions

    def get_ast_by_name(self, name):
        return self.ast.get(name, None)
    
    def get_all_asts(self):
        return self.ast


    