/**
 * @kind problem
 * @id py/dataFlows
 */

import modules.growlithe_dfa.TaintAnalysis
import queries.Config
import semmle.python.dataflow.new.DataFlow
import modules.growlithe_dfa.Core

from DataFlow::Node source, DataFlow::Node sink, string sourceState, string sinkState
where
  TaintAnalysis::MetadataTracker::flow(source, sink) and
  sourceState = TaintAnalysis::getMetadataSourceState(source) and
  sinkState = TaintAnalysis::getMetadataSinkState(sink)
select sink, "$@==>$@", source, sourceState, sink, sinkState
