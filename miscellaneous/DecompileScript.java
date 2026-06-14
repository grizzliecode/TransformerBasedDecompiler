import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.util.task.ConsoleTaskMonitor;
import ghidra.program.model.symbol.*;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;

public class DecompileScript extends GhidraScript {
    @Override
    public void run() throws Exception {
        FunctionManager fm = currentProgram.getFunctionManager();
        SymbolTable symbolTable = currentProgram.getSymbolTable();
        
        for (Symbol symbol : symbolTable.getAllSymbols(true)) {
            if (symbol.getSymbolType() == SymbolType.LABEL && symbol.getName().equals("ghidra_target")) {
                Address addr = symbol.getAddress();
                if (fm.getFunctionAt(addr) == null) {
                    createFunction(addr, symbol.getName());
                }
            }
        }
        
        DecompInterface decompInterface = new DecompInterface();
        decompInterface.openProgram(currentProgram);
        
        println("===START_DECOMPILATION===");
        for (Function func : fm.getFunctions(true)) {
            if (func.getName().equals("ghidra_target")) {
                DecompileResults results = decompInterface.decompileFunction(func, 30, new ConsoleTaskMonitor());
                if (results.decompileCompleted()) {
                    println(results.getDecompiledFunction().getC());
                } else {
                    println("Decompilation failed: " + results.getErrorMessage());
                }
            }
        }
        println("===END_DECOMPILATION===");
    }
}