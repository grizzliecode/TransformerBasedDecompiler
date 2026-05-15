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
        self.anon_functions = {}

    def _translate_ast(self, node, source_code):
        return source_code[node.start_byte:node.end_byte].decode("utf-8")

    def _anonymize_node(self, node, source_code, mapping, counts):
        node_type = node.type
        if node_type in ["identifier", "field_identifier"]:
            name = source_code[node.start_byte:node.end_byte].decode("utf-8")
            if node.parent:
                parent_type = node.parent.type
                if parent_type == "function_declarator" and node.parent.child_by_field_name("declarator") == node:
                    return name
                if parent_type == "call_expression" and node.parent.child_by_field_name("function") == node:
                    return name
            if name not in mapping:
                counts['v'] += 1
                mapping[name] = f"var{counts['v']}"
            return mapping[name]
        if node_type == "type_identifier":
            name = source_code[node.start_byte:node.end_byte].decode("utf-8")
            if name not in mapping:
                counts['t'] += 1
                mapping[name] = f"T{counts['t']}"
            return mapping[name]
        if node.child_count == 0:
            return source_code[node.start_byte:node.end_byte].decode("utf-8")
        parts = []
        last_end = node.start_byte
        for child in node.children:
            parts.append(source_code[last_end:child.start_byte].decode("utf-8"))
            parts.append(self._anonymize_node(child, source_code, mapping, counts))
            last_end = child.end_byte
        return "".join(parts)


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
        mapping = {}
        func_counter = 0
        for func_name in names:
            name_str = self._translate_ast(func_name, source_code)
            if name_str in mapping:
                continue
            func_counter += 1
            mapping[name_str] = f"func{func_counter}"
        counts = {'v': 0, 't': 0}
        definitions = captures.get('function_definition', [])
        for name_node, def_node in zip(names, definitions):
            name_str = self._translate_ast(name_node, source_code)
            func_code = self._translate_ast(def_node, source_code)
            anon_code = self._anonymize_node(def_node, source_code, mapping, counts)
            self.functions[name_str] = func_code
            self.ast[name_str] = str(def_node)
            self.anon_functions[name_str] = anon_code
    

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

    def get_anon_function(self, name):
        return self.anon_functions.get(name, None)


    