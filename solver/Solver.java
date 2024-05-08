package solver;

import org.sat4j.minisat.SolverFactory;
import org.sat4j.reader.DimacsReader;
import org.sat4j.specs.IProblem;
import org.sat4j.specs.ISolver;

public class Solver {

    public static void main(String[] args) {
        try {
            ISolver solver = SolverFactory.newDefault();
            var reader = new DimacsReader(solver);
            IProblem problem = reader.parseInstance(args[0]);
            
            boolean satisfiable = problem.isSatisfiable();

            if (!satisfiable) {
                System.exit(1);
            }

            for (int variable : solver.primeImplicant()) {
                if (variable > 0) {
                    System.out.println(variable);
                }
            }
            
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            System.exit(2);
        }

    }
}
