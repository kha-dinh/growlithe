import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import modules.growlithe_dfa.AdditionalTaints
import modules.growlithe_dfa.Sources
import modules.growlithe_dfa.Sinks
import modules.growlithe_dfa.Core
import queries.Config

module TaintAnalysis {
  // Configuration for main taint tracking
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
      any(AdditionalTaints::AdditionalTaintStep s).step(node1, node2) and
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

  // Configuration for metadata taint tracking
  private module MetadataTrackerConfig implements DataFlow::ConfigSig {
    // Fixed to parameter source to get metadata from
    predicate isSource(DataFlow::Node source) {
      source instanceof Sources::ParameterSource and
      Config::constrainLocation2(source)
    }

    predicate isSink(DataFlow::Node sink) {
      exists(Core::Node n | sink = n.getMetadataSink() and Config::constrainLocation2(n))
    }

    predicate isAdditionalFlowStep(DataFlow::Node node1, DataFlow::Node node2) {
      any(AdditionalTaints::AdditionalTaintStep s).step(node1, node2) and
      Config::constrainLocation2(node1) and
      Config::constrainLocation2(node2)
    }
  }

  /** Global taint tracking for Growlithe metadata flow analysis. */
  module MetadataTracker = TaintTracking::Global<MetadataTrackerConfig>;

  // Helper predicates for metadata tracking
  predicate isMetadataSource(DataFlow::Node source) { MetadataTrackerConfig::isSource(source) }

  predicate isMetadataSink(DataFlow::Node sink) { MetadataTrackerConfig::isSink(sink) }

  string getMetadataSourceState(DataFlow::Node source) {
    isMetadataSource(source) and
    result = source.(Core::Source).getFlowState()
  }

  string getMetadataSinkState(DataFlow::Node sink) {
    isMetadataSink(sink) and
    exists(Core::Node n |
      sink = n.getMetadataSink() and
      (result = n.(Core::Source).getFlowState() or result = n.(Core::Sink).getFlowState())
    )
  }
}
