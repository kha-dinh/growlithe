import python
import semmle.python.dataflow.new.DataFlow

module Config {
  string getFileEndingPattern() {
    result = ["src/function2.py",
		"src/function1.py"]
  }

  string getFunctionName() { result = "lambda_handler" }

  predicate constrainLocation2(DataFlow::Node node) {
    node.getLocation().getFile().getAbsolutePath().matches("%" + getFileEndingPattern())
  }

  predicate constrainLocation(Location loc) {
    loc.getFile().getAbsolutePath().matches("%" + getFileEndingPattern())
  }
}
