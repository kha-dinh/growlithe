/**
 * @kind problem
 * @id js/dataFlows
 */

import javascript
import modules.growlithe_dfa.TaintAnalysis

predicate sourceWithoutFlows(
  DataFlow::Node source, DataFlow::Node sink, string sourceState, string sinkState
) {
  TaintAnalysis::isSource(source) and
  sourceState = TaintAnalysis::getSourceState(source) and
  not TaintAnalysis::Tracker::flow(source, _) and
  source = sink and
  sinkState = "None"
}

predicate sinkWithoutFlows(
  DataFlow::Node source, DataFlow::Node sink, string sourceState, string sinkState
) {
  TaintAnalysis::isSink(sink) and
  sinkState = TaintAnalysis::getSinkState(sink) and
  not TaintAnalysis::Tracker::flow(_, sink) and
  sink.getALocalSource() = source and
  sourceState = "None"
}

predicate taintFlowEdges(
  DataFlow::Node source, DataFlow::Node sink, string sourceState, string sinkState
) {
  TaintAnalysis::Tracker::flow(source, sink) and
  sourceState = TaintAnalysis::getSourceState(source) and
  sinkState = TaintAnalysis::getSinkState(sink)
}

// Query to get valid paths for these dataflows
from DataFlow::Node source, DataFlow::Node sink, string sourceState, string sinkState
where
  taintFlowEdges(source, sink, sourceState, sinkState) or
  sourceWithoutFlows(source, sink, sourceState, sinkState) or
  sinkWithoutFlows(source, sink, sourceState, sinkState)
select sink, "$@==>$@", source, sourceState, sink, sinkState
