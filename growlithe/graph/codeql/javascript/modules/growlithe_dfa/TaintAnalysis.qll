import javascript
import DataFlow
import TaintTracking as TT
import modules.growlithe_dfa.AdditionalTaints
import modules.growlithe_dfa.Sources
import modules.growlithe_dfa.Sinks
import modules.growlithe_dfa.Core
import queries.Config

module TaintAnalysis {
  // Configuration for main taint tracking using the new module-based API
  private module TrackerConfig implements DataFlow::ConfigSig {
    // Add our own sources by modeling them as Core::Source nodes.
    predicate isSource(DataFlow::Node source) {
      source instanceof Core::Source and
      Config::constrainLocation2(source)
    }

    // Add our own sink by modeling them as Core::Sink nodes.
    predicate isSink(DataFlow::Node sink) {
      sink instanceof Core::Sink and
      Config::constrainLocation2(sink)
    }

    // Add additional taint steps by modeling them as
    // AdditionalTaints::AdditionalTaintStep nodes.
    predicate isAdditionalFlowStep(DataFlow::Node node1, DataFlow::Node node2) {
      any(Core::AdditionalTaintStep s).step(node1, node2) and
      Config::constrainLocation2(node1) and
      Config::constrainLocation2(node2)
    }
  }

  /** Global taint tracking for Growlithe dataflow analysis. */
  module Tracker = TaintTracking::Global<TrackerConfig>;

  // Helper predicates to get flow states from nodes
  predicate isSource(DataFlow::Node source) { TrackerConfig::isSource(source) }

  predicate isSink(DataFlow::Node sink) { TrackerConfig::isSink(sink) }

  string getSourceState(DataFlow::Node source) {
    isSource(source) and
    result = source.(Core::Source).getFlowState()
  }

  string getSinkState(DataFlow::Node sink) {
    isSink(sink) and
    result = sink.(Core::Sink).getFlowState()
  }

  // Legacy compatibility predicates for external use
  predicate isGrowlitheSource(DataFlow::Node source, string state) {
    isSource(source) and
    state = getSourceState(source)
  }

  predicate isGrowlitheSink(DataFlow::Node sink, string state) {
    isSink(sink) and
    state = getSinkState(sink)
  }
}
