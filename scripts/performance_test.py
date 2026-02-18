#!/usr/bin/env python3
"""
Performance test script for AI Observability Demo.

This script runs performance tests against the demo application to generate
metrics and traces for observability analysis.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import httpx
import json
from concurrent.futures import ThreadPoolExecutor
import argparse

class PerformanceTest:
    """Performance testing suite for AI Observability Demo."""
    
    def __init__(self, base_url: str = "http://localhost:8080", concurrent_users: int = 5):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.results = []
        
    async def single_request(self, endpoint: str, payload: dict, session: httpx.AsyncClient) -> Dict[str, Any]:
        """Execute a single request and measure performance."""
        start_time = time.time()
        
        try:
            response = await session.post(f"{self.base_url}{endpoint}", json=payload)
            duration = time.time() - start_time
            
            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "duration": duration,
                "success": 200 <= response.status_code < 300,
                "timestamp": start_time,
                "payload_size": len(json.dumps(payload))
            }
            
            if result["success"] and response.headers.get("content-type", "").startswith("application/json"):
                response_data = response.json()
                
                # Extract performance metrics based on endpoint
                if endpoint == "/chat" and "metadata" in response_data:
                    result.update({
                        "tokens_used": response_data["metadata"]["usage"]["total_tokens"],
                        "cost_usd": response_data["metadata"]["cost_usd"]
                    })
                elif endpoint == "/local-inference" and "metadata" in response_data:
                    result.update({
                        "tokens_generated": response_data["metadata"]["usage"]["completion_tokens"],
                        "tokens_per_second": response_data["metadata"]["performance"]["tokens_per_second"]
                    })
                elif endpoint == "/search" and "count" in response_data:
                    result.update({
                        "results_found": response_data["count"]
                    })
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                "endpoint": endpoint,
                "status_code": 0,
                "duration": duration,
                "success": False,
                "error": str(e),
                "timestamp": start_time,
                "payload_size": len(json.dumps(payload))
            }
    
    async def run_chat_performance_test(self, duration_seconds: int = 60) -> List[Dict[str, Any]]:
        """Run chat completion performance test."""
        print(f"Running chat performance test for {duration_seconds} seconds with {self.concurrent_users} concurrent users")
        
        questions = [
            "What is machine learning?",
            "Explain neural networks.",
            "How does AI work?",
            "What is deep learning?",
            "Applications of NLP?"
        ]
        
        end_time = time.time() + duration_seconds
        tasks = []
        
        async with httpx.AsyncClient(timeout=30.0) as session:
            request_count = 0
            
            while time.time() < end_time:
                # Create concurrent requests
                for _ in range(self.concurrent_users):
                    if time.time() >= end_time:
                        break
                        
                    payload = {
                        "message": questions[request_count % len(questions)],
                        "temperature": 0.7,
                        "max_tokens": 150,
                        "user_id": f"perf_test_user_{request_count % self.concurrent_users}"
                    }
                    
                    task = self.single_request("/chat", payload, session)
                    tasks.append(task)
                    request_count += 1
                
                # Wait for batch to complete
                if len(tasks) >= self.concurrent_users * 2:  # Process in batches
                    batch_results = await asyncio.gather(*tasks[:self.concurrent_users])
                    self.results.extend(batch_results)
                    tasks = tasks[self.concurrent_users:]
                    
                    # Print progress
                    if request_count % 10 == 0:
                        success_rate = sum(1 for r in self.results if r["success"]) / len(self.results) * 100
                        avg_duration = statistics.mean([r["duration"] for r in self.results])
                        print(f"Progress: {request_count} requests, {success_rate:.1f}% success rate, {avg_duration:.2f}s avg duration")
            
            # Process remaining tasks
            if tasks:
                remaining_results = await asyncio.gather(*tasks)
                self.results.extend(remaining_results)
        
        return self.results
    
    async def run_mixed_workload_test(self, duration_seconds: int = 300) -> List[Dict[str, Any]]:
        """Run mixed workload performance test."""
        print(f"Running mixed workload test for {duration_seconds} seconds")
        
        workload_patterns = [
            {"endpoint": "/chat", "weight": 40, "payload": {"message": "Test question", "user_id": "perf_user"}},
            {"endpoint": "/search", "weight": 30, "payload": {"query": "machine learning", "n_results": 5, "user_id": "perf_user"}},
            {"endpoint": "/local-inference", "weight": 20, "payload": {"prompt": "AI is", "max_length": 50, "user_id": "perf_user"}},
            {"endpoint": "/embed", "weight": 10, "payload": {"texts": ["Test document"], "store_in_vector_db": False, "user_id": "perf_user"}}
        ]
        
        # Create weighted choices
        choices = []
        for pattern in workload_patterns:
            choices.extend([pattern] * pattern["weight"])
        
        end_time = time.time() + duration_seconds
        tasks = []
        
        async with httpx.AsyncClient(timeout=30.0) as session:
            request_count = 0
            
            while time.time() < end_time:
                # Create concurrent requests with mixed workload
                for _ in range(self.concurrent_users):
                    if time.time() >= end_time:
                        break
                    
                    pattern = choices[request_count % len(choices)]
                    payload = pattern["payload"].copy()
                    payload["user_id"] = f"perf_user_{request_count % self.concurrent_users}"
                    
                    task = self.single_request(pattern["endpoint"], payload, session)
                    tasks.append(task)
                    request_count += 1
                
                # Process in batches
                if len(tasks) >= self.concurrent_users:
                    batch_results = await asyncio.gather(*tasks[:self.concurrent_users])
                    self.results.extend(batch_results)
                    tasks = tasks[self.concurrent_users:]
                    
                    if request_count % 20 == 0:
                        self.print_progress_stats()
                
                await asyncio.sleep(0.1)  # Small delay between batches
            
            # Process remaining tasks
            if tasks:
                remaining_results = await asyncio.gather(*tasks)
                self.results.extend(remaining_results)
        
        return self.results
    
    def print_progress_stats(self):
        """Print current performance statistics."""
        if not self.results:
            return
        
        successful_results = [r for r in self.results if r["success"]]
        
        if not successful_results:
            print(f"Progress: {len(self.results)} requests, 0% success rate")
            return
        
        success_rate = len(successful_results) / len(self.results) * 100
        durations = [r["duration"] for r in successful_results]
        
        stats = {
            "total_requests": len(self.results),
            "success_rate": success_rate,
            "avg_duration": statistics.mean(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p95_duration": statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else max(durations)
        }
        
        print(f"Progress: {stats['total_requests']} requests, "
              f"{stats['success_rate']:.1f}% success, "
              f"avg: {stats['avg_duration']:.2f}s, "
              f"p95: {stats['p95_duration']:.2f}s")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate performance test report."""
        if not self.results:
            return {"error": "No results to analyze"}
        
        successful_results = [r for r in self.results if r["success"]]
        failed_results = [r for r in self.results if not r["success"]]
        
        # Overall statistics
        durations = [r["duration"] for r in successful_results]
        
        overall_stats = {
            "total_requests": len(self.results),
            "successful_requests": len(successful_results),
            "failed_requests": len(failed_results),
            "success_rate": len(successful_results) / len(self.results) * 100,
        }
        
        if durations:
            overall_stats.update({
                "avg_duration": statistics.mean(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "median_duration": statistics.median(durations),
                "std_duration": statistics.stdev(durations) if len(durations) > 1 else 0,
            })
            
            # Percentiles
            if len(durations) >= 10:
                percentiles = statistics.quantiles(durations, n=100)
                overall_stats.update({
                    "p50_duration": percentiles[49],
                    "p95_duration": percentiles[94],
                    "p99_duration": percentiles[98]
                })
        
        # Per-endpoint statistics
        endpoint_stats = {}
        for endpoint in set(r["endpoint"] for r in self.results):
            endpoint_results = [r for r in self.results if r["endpoint"] == endpoint]
            endpoint_successful = [r for r in endpoint_results if r["success"]]
            endpoint_durations = [r["duration"] for r in endpoint_successful]
            
            endpoint_stats[endpoint] = {
                "total_requests": len(endpoint_results),
                "successful_requests": len(endpoint_successful),
                "success_rate": len(endpoint_successful) / len(endpoint_results) * 100 if endpoint_results else 0,
            }
            
            if endpoint_durations:
                endpoint_stats[endpoint].update({
                    "avg_duration": statistics.mean(endpoint_durations),
                    "min_duration": min(endpoint_durations),
                    "max_duration": max(endpoint_durations),
                })
        
        # Error analysis
        error_analysis = {}
        for result in failed_results:
            error_type = result.get("error", f"HTTP {result['status_code']}")
            error_analysis[error_type] = error_analysis.get(error_type, 0) + 1
        
        return {
            "overall_statistics": overall_stats,
            "endpoint_statistics": endpoint_stats,
            "error_analysis": error_analysis,
            "test_configuration": {
                "concurrent_users": self.concurrent_users,
                "base_url": self.base_url
            }
        }

async def main():
    """Main entry point for performance testing."""
    parser = argparse.ArgumentParser(description="AI Observability Demo Performance Test")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Base URL of the demo application")
    parser.add_argument("--concurrent-users", type=int, default=5, help="Number of concurrent users")
    parser.add_argument("--test-type", choices=["chat", "mixed"], default="mixed", help="Type of performance test")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    # Create performance test instance
    perf_test = PerformanceTest(
        base_url=args.base_url,
        concurrent_users=args.concurrent_users
    )
    
    print(f"Starting performance test: {args.test_type}")
    print(f"Target: {args.base_url}")
    print(f"Concurrent users: {args.concurrent_users}")
    print(f"Duration: {args.duration} seconds")
    print("=" * 50)
    
    # Run the specified test
    start_time = time.time()
    
    if args.test_type == "chat":
        await perf_test.run_chat_performance_test(args.duration)
    elif args.test_type == "mixed":
        await perf_test.run_mixed_workload_test(args.duration)
    
    actual_duration = time.time() - start_time
    
    # Generate and display report
    report = perf_test.generate_report()
    
    print("\n" + "=" * 50)
    print("PERFORMANCE TEST RESULTS")
    print("=" * 50)
    
    overall = report["overall_statistics"]
    print(f"Test Duration: {actual_duration:.1f} seconds")
    print(f"Total Requests: {overall['total_requests']}")
    print(f"Success Rate: {overall['success_rate']:.1f}%")
    print(f"Requests/sec: {overall['total_requests'] / actual_duration:.1f}")
    
    if "avg_duration" in overall:
        print(f"Average Response Time: {overall['avg_duration']:.3f}s")
        print(f"Min Response Time: {overall['min_duration']:.3f}s")
        print(f"Max Response Time: {overall['max_duration']:.3f}s")
        
        if "p95_duration" in overall:
            print(f"95th Percentile: {overall['p95_duration']:.3f}s")
            print(f"99th Percentile: {overall['p99_duration']:.3f}s")
    
    print("\nPer-Endpoint Statistics:")
    for endpoint, stats in report["endpoint_statistics"].items():
        print(f"  {endpoint}: {stats['total_requests']} requests, "
              f"{stats['success_rate']:.1f}% success, "
              f"{stats.get('avg_duration', 0):.3f}s avg")
    
    if report["error_analysis"]:
        print("\nError Analysis:")
        for error, count in report["error_analysis"].items():
            print(f"  {error}: {count} occurrences")
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed results saved to: {args.output}")

if __name__ == "__main__":
    asyncio.run(main())