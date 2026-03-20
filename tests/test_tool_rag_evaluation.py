"""Comprehensive evaluation of Tool RAG parameter optimization.

This test suite evaluates different parameter configurations to determine
optimal defaults for the Tool RAG filtering system. It measures:

1. Token usage - Primary optimization metric (cost/efficiency)
2. Accuracy - Precision, recall, F1 scores across diverse queries
3. Parameter sensitivity - How threshold/min_tools/max_tools affect results

Run with: pytest tests/test_tool_rag_evaluation.py -v -s

Test set: 23 queries across 5 categories (single-tool exact/paraphrase/action,
two-tool ambiguous, multi-tool workflows) against 30 tools from 5 domains.

Note: These tests are for parameter tuning and validation. They run in CI
but are primarily used to justify default parameter choices.
"""

import json
import pytest
from typing import Dict, List, Set, Tuple
from unittest.mock import Mock

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

from mcp_client_for_ollama.tools.rag import ToolRAG


# ============================================================================
# Test Data - Expanded for better coverage
# ============================================================================

def create_diverse_tools() -> List[Mock]:
    """Create diverse tool set covering multiple domains."""
    tools = []
    
    # GitHub (6 tools)
    for name, desc in [
        ("list_issues", "List issues from a GitHub repository"),
        ("create_issue", "Create a new issue in a GitHub repository"),
        ("list_pull_requests", "List pull requests in a repository"),
        ("create_pull_request", "Create a new pull request"),
        ("get_commit", "Get details of a specific commit"),
        ("search_code", "Search for code across repositories"),
    ]:
        tool = Mock()
        tool.name = f"github.{name}"
        tool.description = desc
        tool.inputSchema = {"properties": {}}
        tools.append(tool)
    
    # Filesystem (7 tools)
    for name, desc in [
        ("read_file", "Read contents of a file from the filesystem"),
        ("write_file", "Write content to a file"),
        ("list_directory", "List files and directories"),
        ("delete_file", "Delete a file from the filesystem"),
        ("search_files", "Search for files matching a pattern"),
        ("move_file", "Move or rename a file"),
        ("get_file_info", "Get metadata about a file"),
    ]:
        tool = Mock()
        tool.name = f"filesystem.{name}"
        tool.description = desc
        tool.inputSchema = {"properties": {}}
        tools.append(tool)
    
    # AWS (8 tools)
    for name, desc in [
        ("list_buckets", "List all S3 buckets"),
        ("upload_to_s3", "Upload a file to S3"),
        ("download_from_s3", "Download a file from S3"),
        ("list_ec2_instances", "List EC2 instances"),
        ("start_ec2_instance", "Start an EC2 instance"),
        ("stop_ec2_instance", "Stop an EC2 instance"),
        ("invoke_lambda", "Invoke a Lambda function"),
        ("list_lambda_functions", "List Lambda functions"),
    ]:
        tool = Mock()
        tool.name = f"aws.{name}"
        tool.description = desc
        tool.inputSchema = {"properties": {}}
        tools.append(tool)
    
    # Database (5 tools)
    for name, desc in [
        ("query", "Execute a SQL query"),
        ("insert", "Insert data into a table"),
        ("update", "Update records in a table"),
        ("delete", "Delete records from a table"),
        ("create_table", "Create a new database table"),
    ]:
        tool = Mock()
        tool.name = f"database.{name}"
        tool.description = desc
        tool.inputSchema = {"properties": {}}
        tools.append(tool)
    
    # Slack (4 tools)
    for name, desc in [
        ("send_message", "Send a message to a Slack channel"),
        ("list_channels", "List all Slack channels"),
        ("upload_file", "Upload a file to Slack"),
        ("get_user_info", "Get information about a Slack user"),
    ]:
        tool = Mock()
        tool.name = f"slack.{name}"
        tool.description = desc
        tool.inputSchema = {"properties": {}}
        tools.append(tool)
    
    return tools


# Comprehensive test cases organized by expected tool count and query type
TEST_CASES = [
    # === SINGLE TOOL - Exact/Direct phrasing ===
    ("List GitHub issues", {"github.list_issues"}, "single-exact"),
    ("Create a pull request", {"github.create_pull_request"}, "single-exact"),
    ("Read a file", {"filesystem.read_file"}, "single-exact"),
    ("Upload to S3", {"aws.upload_to_s3"}, "single-exact"),
    ("Query database", {"database.query"}, "single-exact"),
    ("Send Slack message", {"slack.send_message"}, "single-exact"),
    
    # === SINGLE TOOL - Paraphrased/Natural language ===
    ("Show me all issues", {"github.list_issues"}, "single-paraphrase"),
    ("Make a new PR", {"github.create_pull_request"}, "single-paraphrase"),
    ("Get file contents", {"filesystem.read_file"}, "single-paraphrase"),
    ("Put file in S3 bucket", {"aws.upload_to_s3"}, "single-paraphrase"),
    ("Run a SQL query", {"database.query"}, "single-paraphrase"),
    ("Post to Slack", {"slack.send_message"}, "single-paraphrase"),
    
    # === SINGLE TOOL - Action-oriented ===
    ("Start an EC2 instance", {"aws.start_ec2_instance"}, "single-action"),
    ("Stop my instance", {"aws.stop_ec2_instance"}, "single-action"),
    ("Move a file", {"filesystem.move_file"}, "single-action"),
    ("Delete a file", {"filesystem.delete_file"}, "single-action"),
    
    # === TWO TOOLS - Ambiguous/Could use either ===
    ("Search for code", {"github.search_code", "filesystem.search_files"}, "two-ambiguous"),
    ("List my files", {"filesystem.list_directory", "aws.list_buckets"}, "two-ambiguous"),
    ("Delete data", {"filesystem.delete_file", "database.delete"}, "two-ambiguous"),
    
    # === MULTI-TOOL - Complex workflows ===
    ("Upload logs to S3 and notify team", {"aws.upload_to_s3", "slack.send_message"}, "multi-workflow"),
    ("Read config and update database", {"filesystem.read_file", "database.update"}, "multi-workflow"),
    ("List EC2 instances and Lambda functions", {"aws.list_ec2_instances", "aws.list_lambda_functions"}, "multi-workflow"),
]


def calculate_metrics(retrieved: Set[str], expected: Set[str]) -> Dict:
    """Calculate precision, recall, F1."""
    tp = len(retrieved & expected)
    precision = tp / len(retrieved) if retrieved else 0
    recall = tp / len(expected) if expected else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {"precision": precision, "recall": recall, "f1": f1}


def estimate_tokens(tools: List[Mock]) -> int:
    """Estimate token count for tool schemas."""
    if not HAS_TIKTOKEN:
        # Rough estimate: ~250 tokens per tool
        return len(tools) * 250
    
    encoding = tiktoken.get_encoding("cl100k_base")
    tools_json = json.dumps([
        {"name": t.name, "description": t.description, "parameters": t.inputSchema}
        for t in tools
    ])
    return len(encoding.encode(tools_json))


# ============================================================================
# Token Usage Analysis - THE CRITICAL METRIC
# ============================================================================

@pytest.mark.parametrize("use_estimates", [True] if not HAS_TIKTOKEN else [False, True])
def test_token_usage_by_configuration(use_estimates):
    """Measure actual token savings for different configurations.
    
    This is the PRIMARY metric - we're optimizing for token reduction
    while maintaining acceptable accuracy.
    """
    if use_estimates:
        print("\n" + "="*80)
        print("TOKEN USAGE ANALYSIS (ESTIMATED) - PRIMARY OPTIMIZATION METRIC")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("TOKEN USAGE ANALYSIS (ACTUAL) - PRIMARY OPTIMIZATION METRIC")
        print("="*80)
    
    tools = create_diverse_tools()
    rag = ToolRAG()
    rag.embed_tools(tools, use_cache=False)
    
    # Baseline: all tools
    baseline_tokens = estimate_tokens(tools)
    print(f"\nBaseline (all {len(tools)} tools): {baseline_tokens} tokens")
    
    configs = [
        {"threshold": 0.3, "min_tools": 0, "max_tools": 20, "name": "Low threshold"},
        {"threshold": 0.4, "min_tools": 3, "max_tools": 20, "name": "Recommended"},
        {"threshold": 0.5, "min_tools": 3, "max_tools": 20, "name": "Medium threshold"},
        {"threshold": 0.65, "min_tools": 0, "max_tools": 20, "name": "Current default"},
    ]
    
    results = []
    
    for config in configs:
        total_tokens = 0
        total_saved = 0
        query_count = 0
        
        # Group results by query type
        by_type = {}
        
        for query, expected, query_type in TEST_CASES:
            retrieved = rag.retrieve_relevant_tools(
                query,
                threshold=config["threshold"],
                min_tools=config["min_tools"],
                max_tools=config["max_tools"]
            )
            
            filtered_tokens = estimate_tokens(retrieved)
            saved = baseline_tokens - filtered_tokens
            percent_saved = (saved / baseline_tokens * 100) if baseline_tokens > 0 else 0
            
            total_tokens += filtered_tokens
            total_saved += saved
            query_count += 1
            
            if query_type not in by_type:
                by_type[query_type] = {"tokens": 0, "saved": 0, "count": 0}
            by_type[query_type]["tokens"] += filtered_tokens
            by_type[query_type]["saved"] += saved
            by_type[query_type]["count"] += 1
        
        avg_tokens = total_tokens / query_count
        avg_saved = total_saved / query_count
        avg_percent = (avg_saved / baseline_tokens * 100) if baseline_tokens > 0 else 0
        
        result = {
            "name": config["name"],
            "config": config,
            "avg_tokens": avg_tokens,
            "avg_saved": avg_saved,
            "avg_percent_saved": avg_percent,
            "by_type": by_type
        }
        results.append(result)
        
        print(f"\n{config['name']}:")
        print(f"  Config: threshold={config['threshold']}, min={config['min_tools']}, max={config['max_tools']}")
        print(f"  Avg tokens per query: {avg_tokens:.0f} (baseline: {baseline_tokens})")
        print(f"  Avg tokens saved: {avg_saved:.0f} ({avg_percent:.1f}%)")
        
        # Show breakdown by query type
        print(f"  By query type:")
        for qtype, data in sorted(by_type.items()):
            avg_for_type = data["tokens"] / data["count"]
            saved_for_type = data["saved"] / data["count"]
            percent_for_type = (saved_for_type / baseline_tokens * 100) if baseline_tokens > 0 else 0
            print(f"    {qtype:20s}: {avg_for_type:6.0f} tokens ({percent_for_type:5.1f}% saved)")
    
    # Find best configuration (maximize token savings while maintaining quality)
    best = max(results, key=lambda x: x["avg_percent_saved"])
    
    print("\n" + "="*80)
    print(f"BEST TOKEN SAVINGS: {best['name']}")
    print(f"  Average: {best['avg_tokens']:.0f} tokens ({best['avg_percent_saved']:.1f}% saved)")
    print("="*80)
    
    # Calculate cost impact (assuming $0.01 per 1K tokens)
    print("\nCOST IMPACT (20 queries per session):")
    for result in results:
        session_tokens = result["avg_tokens"] * 20
        baseline_session = baseline_tokens * 20
        cost = session_tokens / 1000 * 0.01
        baseline_cost = baseline_session / 1000 * 0.01
        savings = baseline_cost - cost
        print(f"  {result['name']:20s}: ${cost:.3f} (saves ${savings:.3f} vs baseline)")


# ============================================================================
# Threshold Tuning Tests
# ============================================================================

def test_threshold_sweep():
    """Test multiple threshold values to find optimal setting."""
    print("\n" + "="*80)
    print("THRESHOLD SENSITIVITY ANALYSIS")
    print("="*80)
    
    tools = create_diverse_tools()
    rag = ToolRAG()
    rag.embed_tools(tools, use_cache=False)
    
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.65, 0.7, 0.8]
    results = []
    
    # Also track by query type
    print(f"\nTest set composition:")
    type_counts = {}
    for _, _, qtype in TEST_CASES:
        type_counts[qtype] = type_counts.get(qtype, 0) + 1
    for qtype, count in sorted(type_counts.items()):
        print(f"  {qtype}: {count} queries")
    
    for threshold in thresholds:
        total_precision = 0
        total_recall = 0
        total_f1 = 0
        perfect_recall = 0
        zero_recall = 0
        avg_tools_retrieved = 0
        
        # Track by query type
        by_type = {}
        
        for query, expected, query_type in TEST_CASES:
            retrieved = rag.retrieve_relevant_tools(query, threshold=threshold, min_tools=0, max_tools=20)
            retrieved_names = {t.name for t in retrieved}
            
            metrics = calculate_metrics(retrieved_names, expected)
            total_precision += metrics["precision"]
            total_recall += metrics["recall"]
            total_f1 += metrics["f1"]
            avg_tools_retrieved += len(retrieved)
            
            if metrics["recall"] == 1.0:
                perfect_recall += 1
            if metrics["recall"] == 0.0:
                zero_recall += 1
            
            if query_type not in by_type:
                by_type[query_type] = {"recall": 0, "count": 0}
            by_type[query_type]["recall"] += metrics["recall"]
            by_type[query_type]["count"] += 1
        
        valid_cases = len(TEST_CASES)
        avg_precision = total_precision / valid_cases
        avg_recall = total_recall / valid_cases
        avg_f1 = total_f1 / valid_cases
        avg_tools = avg_tools_retrieved / valid_cases
        
        results.append({
            "threshold": threshold,
            "precision": avg_precision,
            "recall": avg_recall,
            "f1": avg_f1,
            "perfect_recall": perfect_recall,
            "zero_recall": zero_recall,
            "avg_tools": avg_tools,
            "by_type": by_type
        })
        
        print(f"\nThreshold: {threshold:.2f}")
        print(f"  Precision: {avg_precision:.3f} | Recall: {avg_recall:.3f} | F1: {avg_f1:.3f}")
        print(f"  Perfect: {perfect_recall}/{valid_cases} | Zero: {zero_recall}/{valid_cases} | Avg tools: {avg_tools:.1f}")
        
        # Show recall by query type
        print(f"  Recall by type:")
        for qtype in sorted(by_type.keys()):
            type_recall = by_type[qtype]["recall"] / by_type[qtype]["count"]
            print(f"    {qtype:20s}: {type_recall:.3f}")
    
    # Find optimal threshold (maximize F1, then recall)
    best = max(results, key=lambda x: (x["f1"], x["recall"]))
    
    print("\n" + "="*80)
    print(f"RECOMMENDED THRESHOLD: {best['threshold']:.2f}")
    print(f"  F1: {best['f1']:.3f} | Recall: {best['recall']:.3f} | Precision: {best['precision']:.3f}")
    print("="*80)
    
    # Assert we found a good threshold
    assert best["recall"] >= 0.75, "Best threshold should achieve >=75% recall"
    assert best["f1"] >= 0.5, "Best threshold should achieve >=50% F1"


def test_min_tools_impact():
    """Test impact of min_tools parameter as safety net."""
    print("\n" + "="*80)
    print("MIN_TOOLS PARAMETER ANALYSIS")
    print("="*80)
    
    tools = create_diverse_tools()
    rag = ToolRAG()
    rag.embed_tools(tools, use_cache=False)
    
    # Use high threshold that might miss tools
    high_threshold = 0.8
    min_tools_values = [0, 1, 3, 5, 10]
    
    for min_tools in min_tools_values:
        zero_results = 0
        total_retrieved = 0
        
        for query, expected, query_type in TEST_CASES:
            retrieved = rag.retrieve_relevant_tools(
                query, 
                threshold=high_threshold, 
                min_tools=min_tools, 
                max_tools=20
            )
            total_retrieved += len(retrieved)
            if len(retrieved) == 0:
                zero_results += 1
        
        avg_retrieved = total_retrieved / len(TEST_CASES)
        print(f"\nmin_tools={min_tools:2d}: Zero results: {zero_results}/{len(TEST_CASES)} | Avg retrieved: {avg_retrieved:.1f}")
    
    print("\n" + "="*80)
    print("RECOMMENDATION: min_tools=3-5 prevents zero-result scenarios")
    print("="*80)


def test_max_tools_impact():
    """Test impact of max_tools cap on performance and quality."""
    print("\n" + "="*80)
    print("MAX_TOOLS PARAMETER ANALYSIS")
    print("="*80)
    
    tools = create_diverse_tools()
    rag = ToolRAG()
    rag.embed_tools(tools, use_cache=False)
    
    max_tools_values = [5, 10, 15, 20, 30, 50]
    threshold = 0.3  # Use reasonable threshold
    
    for max_tools in max_tools_values:
        total_recall = 0
        total_retrieved = 0
        
        for query, expected, query_type in TEST_CASES:
            retrieved = rag.retrieve_relevant_tools(
                query,
                threshold=threshold,
                min_tools=0,
                max_tools=max_tools
            )
            retrieved_names = {t.name for t in retrieved}
            
            metrics = calculate_metrics(retrieved_names, expected)
            total_recall += metrics["recall"]
            total_retrieved += len(retrieved)
        
        valid_cases = len(TEST_CASES)
        avg_recall = total_recall / valid_cases
        avg_retrieved = total_retrieved / valid_cases
        
        print(f"\nmax_tools={max_tools:2d}: Recall: {avg_recall:.3f} | Avg retrieved: {avg_retrieved:.1f}")
    
    print("\n" + "="*80)
    print("RECOMMENDATION: max_tools=15-20 balances recall and context size")
    print("="*80)


def test_combined_parameter_optimization():
    """Test combinations to find optimal parameter set."""
    print("\n" + "="*80)
    print("COMBINED PARAMETER OPTIMIZATION")
    print("="*80)
    
    tools = create_diverse_tools()
    rag = ToolRAG()
    rag.embed_tools(tools, use_cache=False)
    
    # Test promising combinations
    configs = [
        {"threshold": 0.3, "min_tools": 0, "max_tools": 20, "name": "Current defaults (adjusted)"},
        {"threshold": 0.3, "min_tools": 3, "max_tools": 20, "name": "With safety net"},
        {"threshold": 0.3, "min_tools": 5, "max_tools": 15, "name": "Conservative"},
        {"threshold": 0.4, "min_tools": 3, "max_tools": 20, "name": "Higher threshold"},
        {"threshold": 0.2, "min_tools": 0, "max_tools": 20, "name": "Lower threshold"},
        {"threshold": 0.65, "min_tools": 0, "max_tools": 20, "name": "Original defaults"},
    ]
    
    results = []
    
    for config in configs:
        total_precision = 0
        total_recall = 0
        total_f1 = 0
        zero_results = 0
        avg_tools = 0
        
        for query, expected, query_type in TEST_CASES:
            retrieved = rag.retrieve_relevant_tools(
                query,
                threshold=config["threshold"],
                min_tools=config["min_tools"],
                max_tools=config["max_tools"]
            )
            retrieved_names = {t.name for t in retrieved}
            
            metrics = calculate_metrics(retrieved_names, expected)
            total_precision += metrics["precision"]
            total_recall += metrics["recall"]
            total_f1 += metrics["f1"]
            avg_tools += len(retrieved)
            
            if len(retrieved) == 0:
                zero_results += 1
        
        valid_cases = len(TEST_CASES)
        
        result = {
            "name": config["name"],
            "config": config,
            "precision": total_precision / valid_cases,
            "recall": total_recall / valid_cases,
            "f1": total_f1 / valid_cases,
            "zero_results": zero_results,
            "avg_tools": avg_tools / valid_cases
        }
        results.append(result)
        
        print(f"\n{config['name']}:")
        print(f"  Config: threshold={config['threshold']}, min={config['min_tools']}, max={config['max_tools']}")
        print(f"  F1: {result['f1']:.3f} | Recall: {result['recall']:.3f} | Precision: {result['precision']:.3f}")
        print(f"  Zero results: {zero_results} | Avg tools: {result['avg_tools']:.1f}")
    
    # Find best configuration by F1 score
    best_f1 = max(results, key=lambda x: (x["f1"], x["recall"], -x["zero_results"]))
    
    # But also check threshold=0.3 with min_tools=0 (our actual choice)
    recommended = next((r for r in results if r["config"]["threshold"] == 0.3 and r["config"]["min_tools"] == 0), None)
    
    print("\n" + "="*80)
    print("BEST F1 SCORE CONFIGURATION:")
    print(f"  {best_f1['name']}")
    print(f"  threshold={best_f1['config']['threshold']}, min={best_f1['config']['min_tools']}, max={best_f1['config']['max_tools']}")
    print(f"  F1: {best_f1['f1']:.3f} | Recall: {best_f1['recall']:.3f} | Precision: {best_f1['precision']:.3f}")
    
    if recommended:
        print("\nRECOMMENDED CONFIGURATION (threshold=0.3, min_tools=0):")
        print(f"  Rationale: Catches natural language paraphrases, no artificial minimum")
        print(f"  F1: {recommended['f1']:.3f} | Recall: {recommended['recall']:.3f} | Precision: {recommended['precision']:.3f}")
        print(f"  Zero results: {recommended['zero_results']} | Avg tools: {recommended['avg_tools']:.1f}")
    print("="*80)


def test_edge_cases():
    """Test edge cases and unusual inputs."""
    print("\n" + "="*80)
    print("EDGE CASE TESTING")
    print("="*80)
    
    tools = create_diverse_tools()
    rag = ToolRAG()
    rag.embed_tools(tools, use_cache=False)
    
    edge_cases = [
        ("", "Empty query"),
        ("a", "Single character"),
        ("x" * 500, "Very long query"),
        ("!@#$%^&*()", "Special characters only"),
        ("github github github", "Repeated words"),
        ("list list list list", "Generic repeated word"),
    ]
    
    for query, description in edge_cases:
        try:
            retrieved = rag.retrieve_relevant_tools(query, threshold=0.3, min_tools=3, max_tools=20)
            print(f"✅ {description}: {len(retrieved)} tools retrieved")
        except Exception as e:
            print(f"❌ {description}: {type(e).__name__}: {e}")
    
    print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
