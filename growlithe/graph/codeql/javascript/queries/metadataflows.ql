/**
 * @kind problem
 * @id js/metadataFlows
 */

import javascript
import modules.growlithe_dfa.TaintAnalysis
import queries.Config

from DataFlow::Node source, DataFlow::Node sink, string sourceState, string sinkState
where
  TaintAnalysis::MetadataTracker::flow(source, sink) and
  sourceState = TaintAnalysis::getMetadataSourceState(source) and
  sinkState = TaintAnalysis::getMetadataSinkState(sink)
select sink, "$@==>$@", source, sourceState, sink, sinkState
