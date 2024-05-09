package solver;

import java.io.RandomAccessFile;
import java.util.ArrayList;
import java.util.List;

import org.sat4j.core.VecInt;
import org.sat4j.minisat.SolverFactory;
import org.sat4j.reader.DimacsReader;
import org.sat4j.specs.IProblem;
import org.sat4j.specs.IVecInt;


public class Solver {
    static void try_assumption_one(IProblem problem,
                                   IVecInt assumptions,
                                   List<Integer> all_assumptions,
                                   int i) throws Exception
    {
        assumptions.push(all_assumptions.get(i));

        boolean satisfiable = problem.isSatisfiable(assumptions);

        if (!satisfiable) {
            assumptions.pop();
        }
    }

    static boolean try_assumption_chunk(IProblem problem,
                                        IVecInt assumptions,
                                        List<Integer> all_assumptions,
                                        int begin,
                                        int end) throws Exception
    {
        for (int i = begin; i != end; i++) {
            assumptions.push(all_assumptions.get(i));
        }

        boolean satisfiable = problem.isSatisfiable(assumptions);

        if (!satisfiable) {
            assumptions.shrink(end - begin);
        }

        return satisfiable;
    }

    static void try_assumptions_half(IProblem problem,
                                     IVecInt assumptions,
                                     List<Integer> all_assumptions,
                                     int begin,
                                     int end) throws Exception
    {
        boolean left_satisfiable = try_assumption_chunk(problem, assumptions, all_assumptions, begin, end);

        if (!left_satisfiable)
        {
            try_assumptions(problem, assumptions, all_assumptions, begin, end);
        }
    }

    static void try_assumptions(IProblem problem,
                                IVecInt assumptions,
                                List<Integer> all_assumptions,
                                int begin,
                                int end) throws Exception
    {
        int size = end - begin;

        if (size == 1) {
            try_assumption_one(problem, assumptions, all_assumptions, begin);
        } else {
            int middle = begin + size / 2;

            try_assumptions_half(problem, assumptions, all_assumptions, begin, middle);
            try_assumptions_half(problem, assumptions, all_assumptions, middle, end);
        }
    }
    
    static List<Integer> read_assumptions(String path) throws Exception
    {
        RandomAccessFile file = new RandomAccessFile(path, "r");
        String line;
        List<Integer> assumptions = new ArrayList<Integer>();

        while ((line = file.readLine()) != null) {
            int literal = Integer.valueOf(line);
            assumptions.add(literal);
        }

        file.close();

        return assumptions;
    }

    public static void main(String[] args) {
        try {
            var solver = SolverFactory.newDefault();
            var reader = new DimacsReader(solver);
            var problem = reader.parseInstance(args[0]);
            
            var all_assumptions = read_assumptions(args[1]);
            
            var assumptions = new VecInt();

            boolean satisfiable = problem.isSatisfiable();
            
            if (satisfiable)
            {
                if (all_assumptions.size() > 0)
                {
                    try_assumptions(problem, assumptions, all_assumptions, 0, all_assumptions.size());
                }
            }
            else
            {
                System.err.println("UNSAT");
                System.exit(1);
            }

            problem.isSatisfiable(assumptions);

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
