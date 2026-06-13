from codebleu import calc_codebleu
from typing import Tuple
import tree_sitter_c as tsc
from tree_sitter import Language, Parser    
import math
import re
from rapidfuzz.distance import Levenshtein


class DecompileEvaluatorException(Exception):
    def __init__(self, message):
        super().__init__(message)

class DecompileEvaluator:
    def __init__(self, cb_weigths: Tuple[float, float, float, float] = (0.1,0.2,0.4,0.3), functionality_weigth: float = (0.8), readability_weight: float = 0.15, identity_weight: float=0.05):
        w1,w2,w3,w4 = cb_weigths
        if not (0 <= w1 <= 1 and 0 <= w2 <= 1 and 0 <= w3 <= 1 and 0 <= w4 <= 1):
            raise DecompileEvaluatorException("CodeBLEU weights must be between 0 and 1")
        if not (0 <= functionality_weigth <= 1 and 0 <= readability_weight <= 1 and 0 <= identity_weight <= 1):
            raise DecompileEvaluatorException("Functionality, Readability, and Identity weights must be between 0 and 1")
        if w1 + w2 + w3 + w4 != 1:
            raise DecompileEvaluatorException("CodeBLEU weights must sum to 1")
        if functionality_weigth + readability_weight + identity_weight != 1:
            raise DecompileEvaluatorException("Functionality, Readability, and Identity weights must sum to 1")
        self.cb_weights = cb_weigths
        self.functionality_weight = functionality_weigth
        self.readability_weight = readability_weight
        self.identity_weight = identity_weight
        C_LANGUAGE = Language(tsc.language())
        self.parser = Parser(C_LANGUAGE)
        self.LENGTH_WEIGHT = 0.6
        self.OPERATOR_WEIGHT = 0.3
        self.FUNCTION_CALL_WEIGHT = 0.1
        self.LENGTH_THRESHOLD = 80
        self.OPERATORS_THRESHOLD = 10
        self.FUNCTION_CALLS_THRESHOLD = 3

    def _evaluate_functionality(self, reference_code: str, output_code: str) -> float:
        print(calc_codebleu([reference_code], [output_code], lang="c",weights=self.cb_weights))
        return calc_codebleu([reference_code], [output_code], lang="c",weights=self.cb_weights)["codebleu"]

    def _get_number_of_special_operators(self,line: str) -> int:
        special_operators = ['>>', '<<', '~', '^', '|', '&', '!', '||', '&&', '<=', '>=', '<', '>', '!=', '==', '--', '++', '%', '/', '*', '-', '+', ']', '[', ')', '(', '=']
        count = 0
        for op in special_operators:
            count += line.count(op)
            line = line.replace(op, ' ')
        return count

    def traverse(self,node):
        function_calls = 0
        if node.type == 'call_expression':
            function_calls += 1
        for child in node.children:
            function_calls += self.traverse(child)
        return function_calls

    def _get_number_of_function_calls(self, line:str) -> int:
        lineB = bytes(line, 'utf8')
        node = self.parser.parse(lineB).root_node
        function_calls = self.traverse(node)
        return function_calls

    def evaluate_readability(self, output_code: str) -> float:
        total_score = 0
        for line in output_code.splitlines():
            l = len(line)
            nop = self._get_number_of_special_operators(line)
            nfc = self._get_number_of_function_calls(line)
            l_score = min(1, math.exp(-(l-self.LENGTH_THRESHOLD)/self.LENGTH_THRESHOLD))
            op_score = min(1, math.exp(-(nop-self.OPERATORS_THRESHOLD)/self.OPERATORS_THRESHOLD))
            fc_score = min(1, math.exp(-(nfc-self.FUNCTION_CALLS_THRESHOLD)/self.FUNCTION_CALLS_THRESHOLD))
            line_score = self.LENGTH_WEIGHT * l_score + self.OPERATOR_WEIGHT * op_score + self.FUNCTION_CALL_WEIGHT * fc_score
            total_score += line_score * line_score
        total_score = math.sqrt(total_score / len(output_code.splitlines()))
        return total_score

    def get_tokens(self, code: str) -> list:
        return re.findall(r'\w+|[^\s\w]', code)

    def _edit_distance(self, s1: str, s2: str) -> int:
        s1_tokens = self.get_tokens(s1)
        s2_tokens = self.get_tokens(s2)
        mx_len = max(len(s1_tokens), len(s2_tokens))
        if mx_len == 0:
            return 0
        distance = Levenshtein.distance(s1_tokens, s2_tokens)
        return distance

    def evaluate_identity(self, reference_code: str, output_code: str) -> float:
        identity_score =1 - self._edit_distance(reference_code, output_code) / max(len(self.get_tokens(reference_code)), len(self.get_tokens(output_code)))
        return identity_score

    def evaluate_decompile(self, referenced_code: str, output_code: str) -> float:
        functionality_score = self._evaluate_functionality(referenced_code, output_code)
        readability_score = self.evaluate_readability(output_code)
        identity_score = self.evaluate_identity(referenced_code, output_code)
        print(f"Functionality Score: {functionality_score:.4f}")
        print(f"Readability Score: {readability_score:.4f}")
        print(f"Identity Score: {identity_score:.4f}")
        return (self.functionality_weight * functionality_score +
                self.readability_weight * readability_score +
                self.identity_weight * identity_score)

if __name__ == "__main__":
    ref = "int var1 = env_func_0(var2);"
    gen = "int var10 = env_func_0(var2);"
    evaluator = DecompileEvaluator()
    score = evaluator.evaluate_decompile(ref, gen)
    print(f"Decompilation Score: {score:.4f}")