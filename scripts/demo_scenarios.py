#!/usr/bin/env python3
"""
Demo scenarios for AI Observability Demo.

This script demonstrates various AI workflows with comprehensive observability:
1. Chat completions with different models
2. Embedding generation and vector storage
3. Similarity search operations
4. Local model inference
5. Full pipeline demonstrations
6. Error scenarios for observability testing
"""

import asyncio
import time
import json
import random
from typing import List, Dict, Any
import httpx
import structlog
from dotenv import load_dotenv
import os

load_dotenv()

logger = structlog.get_logger(__name__)

class DemoScenarios:
    """AI Observability Demo Scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Sample data for demonstrations
        self.sample_questions = [
            "What is artificial intelligence and how does it work?",
            "Explain the difference between machine learning and deep learning.",
            "How do neural networks process information?",
            "What are the applications of natural language processing?",
            "Describe the concept of computer vision in AI.",
            "What is reinforcement learning and where is it used?",
            "How do transformer models work in language processing?",
            "What are the ethical considerations in AI development?",
            "Explain the role of data in machine learning.",
            "What is the future of artificial intelligence?"
        ]
        
        self.sample_documents = [
            "Artificial intelligence is a branch of computer science that aims to create intelligent machines.",
            "Machine learning is a subset of AI that enables computers to learn from data without explicit programming.",
            "Deep learning uses neural networks with multiple layers to model complex patterns in data.",
            "Natural language processing helps computers understand and generate human language.",
            "Computer vision enables machines to interpret and analyze visual information from images and videos.",
            "Reinforcement learning trains agents to make decisions through interaction with an environment.",
            "Transformer models use attention mechanisms to process sequential data effectively.",
            "AI ethics focuses on ensuring AI systems are fair, transparent, and beneficial to society.",
            "Quality data is essential for training accurate and reliable machine learning models.",
            "The future of AI includes advancements in AGI, robotics, and human-AI collaboration."
        ]
        
        self.user_profiles = [
            {"user_id": "researcher_001", "role": "researcher", "expertise": "high"},
            {"user_id": "student_001", "role": "student", "expertise": "beginner"},
            {"user_id": "developer_001", "role": "developer", "expertise": "intermediate"},
            {"user_id": "analyst_001", "role": "analyst", "expertise": "intermediate"},
            {"user_id": "executive_001", "role": "executive", "expertise": "low"}
        ]

    async def health_check(self) -> bool:
        """Check if the demo application is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                logger.info("Application is healthy", health_data=response.json())
                return True
            else:
                logger.error("Application health check failed", status_code=response.status_code)
                return False
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False

    async def scenario_chat_completions(self) -> None:
        """Demonstrate chat completions with observability."""
        logger.info("=== Running Chat Completion Scenarios ===")
        
        for i, (question, user) in enumerate(zip(self.sample_questions[:5], self.user_profiles)):
            logger.info(f"Chat scenario {i+1}/5", question=question[:50], user_id=user["user_id"])
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat",
                    json={
                        "message": question,
                        "temperature": random.uniform(0.5, 1.0),
                        "max_tokens": random.randint(100, 300),
                        "user_id": user["user_id"],
                        "session_id": f"session_{i+1}"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "Chat completion successful",
                        tokens_used=result["metadata"]["usage"]["total_tokens"],
                        cost=result["metadata"]["cost_usd"],
                        duration=result["metadata"]["duration_seconds"]
                    )
                else:
                    logger.error("Chat completion failed", status_code=response.status_code)
                
                # Add some delay between requests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("Chat completion error", error=str(e))

    async def scenario_embeddings_and_search(self) -> None:
        """Demonstrate embedding generation and vector search."""
        logger.info("=== Running Embedding and Search Scenarios ===")
        
        # First, generate and store embeddings for sample documents
        logger.info("Generating embeddings for sample documents")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/embed",
                json={
                    "texts": self.sample_documents,
                    "store_in_vector_db": True,
                    "metadata": [
                        {"type": "knowledge_base", "topic": "ai_basics", "index": i}
                        for i in range(len(self.sample_documents))
                    ],
                    "user_id": "system"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    "Embeddings created and stored",
                    embeddings_count=result["embeddings_created"],
                    cost=result["metadata"]["cost_usd"]
                )
            else:
                logger.error("Embedding creation failed", status_code=response.status_code)
                return
                
        except Exception as e:
            logger.error("Embedding creation error", error=str(e))
            return
        
        # Wait a moment for storage to complete
        await asyncio.sleep(2)
        
        # Now perform searches
        search_queries = [
            "What is machine learning?",
            "How do neural networks work?",
            "Applications of AI in vision",
            "Ethics in artificial intelligence"
        ]
        
        for i, query in enumerate(search_queries):
            logger.info(f"Search scenario {i+1}/{len(search_queries)}", query=query)
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/search",
                    json={
                        "query": query,
                        "n_results": 3,
                        "user_id": f"searcher_{i+1}"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "Search completed",
                        results_found=result["count"],
                        total_duration=result["metadata"]["total_duration_seconds"]
                    )
                    
                    # Log top result for demonstration
                    if result["results"]:
                        top_result = result["results"][0]
                        logger.info(
                            "Top search result",
                            similarity=top_result["similarity"],
                            document=top_result["document"][:100]
                        )
                else:
                    logger.error("Search failed", status_code=response.status_code)
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("Search error", error=str(e))

    async def scenario_local_inference(self) -> None:
        """Demonstrate local model inference."""
        logger.info("=== Running Local Model Inference Scenarios ===")
        
        prompts = [
            "The future of artificial intelligence is",
            "Machine learning helps us to",
            "In the world of technology,",
            "Data science is important because"
        ]
        
        for i, prompt in enumerate(prompts):
            logger.info(f"Local inference scenario {i+1}/{len(prompts)}", prompt=prompt)
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/local-inference",
                    json={
                        "prompt": prompt,
                        "max_length": random.randint(80, 150),
                        "temperature": random.uniform(0.6, 0.9),
                        "num_sequences": 1,
                        "user_id": f"local_user_{i+1}"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "Local inference completed",
                        tokens_generated=result["metadata"]["usage"]["completion_tokens"],
                        tokens_per_second=result["metadata"]["performance"]["tokens_per_second"],
                        device=result["metadata"]["device"]
                    )
                    
                    # Log generated text
                    if result["generated_texts"]:
                        logger.info("Generated text", text=result["generated_texts"][0][:100])
                        
                else:
                    logger.error("Local inference failed", status_code=response.status_code)
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("Local inference error", error=str(e))

    async def scenario_full_pipeline(self) -> None:
        """Demonstrate the full AI pipeline with all components."""
        logger.info("=== Running Full Pipeline Scenarios ===")
        
        pipeline_queries = [
            "Explain machine learning in simple terms",
            "What are the benefits of deep learning?",
            "How is AI used in healthcare?"
        ]
        
        for i, query in enumerate(pipeline_queries):
            logger.info(f"Full pipeline scenario {i+1}/{len(pipeline_queries)}", query=query)
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/full-pipeline",
                    params={
                        "query": query,
                        "store_results": True,
                        "user_id": f"pipeline_user_{i+1}"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    summary = result["summary"]
                    
                    logger.info(
                        "Full pipeline completed",
                        total_duration=summary["total_duration_seconds"],
                        total_cost=summary["total_cost_usd"],
                        openai_tokens=summary["openai_tokens_used"],
                        local_tokens=summary["local_tokens_generated"],
                        documents_stored=summary["documents_stored"],
                        search_results=summary["search_results_found"]
                    )
                    
                else:
                    logger.error("Full pipeline failed", status_code=response.status_code)
                    
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error("Full pipeline error", error=str(e))

    async def scenario_error_conditions(self) -> None:
        """Demonstrate error conditions for observability testing."""
        logger.info("=== Running Error Condition Scenarios ===")
        
        # Test various error conditions
        error_scenarios = [
            {
                "name": "Invalid OpenAI model",
                "endpoint": "/chat",
                "payload": {
                    "message": "Test message",
                    "model": "invalid-model-name",
                    "user_id": "error_test_1"
                }
            },
            {
                "name": "Empty message",
                "endpoint": "/chat", 
                "payload": {
                    "message": "",
                    "user_id": "error_test_2"
                }
            },
            {
                "name": "Invalid temperature",
                "endpoint": "/local-inference",
                "payload": {
                    "prompt": "Test prompt",
                    "temperature": 5.0,  # Too high
                    "user_id": "error_test_3"
                }
            },
            {
                "name": "Negative n_results",
                "endpoint": "/search",
                "payload": {
                    "query": "Test query",
                    "n_results": -1,
                    "user_id": "error_test_4"
                }
            }
        ]
        
        for scenario in error_scenarios:
            logger.info(f"Testing error scenario: {scenario['name']}")
            
            try:
                response = await self.client.post(
                    f"{self.base_url}{scenario['endpoint']}",
                    json=scenario["payload"]
                )
                
                logger.info(
                    "Error scenario result",
                    scenario=scenario["name"],
                    status_code=response.status_code,
                    expected_error=response.status_code >= 400
                )
                
            except Exception as e:
                logger.info(
                    "Error scenario exception (expected)",
                    scenario=scenario["name"],
                    error=str(e)
                )
            
            await asyncio.sleep(0.5)

    async def scenario_load_simulation(self, duration_minutes: int = 5) -> None:
        """Simulate load for observability testing."""
        logger.info(f"=== Running Load Simulation for {duration_minutes} minutes ===")
        
        end_time = time.time() + (duration_minutes * 60)
        request_count = 0
        
        while time.time() < end_time:
            # Randomly choose a scenario type
            scenario_type = random.choice([
                "chat", "search", "local_inference", "embed"
            ])
            
            user = random.choice(self.user_profiles)
            
            try:
                if scenario_type == "chat":
                    question = random.choice(self.sample_questions)
                    response = await self.client.post(
                        f"{self.base_url}/chat",
                        json={
                            "message": question,
                            "temperature": random.uniform(0.5, 1.0),
                            "user_id": user["user_id"]
                        }
                    )
                
                elif scenario_type == "search":
                    query = random.choice(self.sample_questions)
                    response = await self.client.post(
                        f"{self.base_url}/search",
                        json={
                            "query": query,
                            "n_results": random.randint(2, 5),
                            "user_id": user["user_id"]
                        }
                    )
                
                elif scenario_type == "local_inference":
                    prompt = random.choice(self.sample_questions[:3])  # Shorter prompts
                    response = await self.client.post(
                        f"{self.base_url}/local-inference",
                        json={
                            "prompt": prompt,
                            "max_length": random.randint(50, 100),
                            "user_id": user["user_id"]
                        }
                    )
                
                elif scenario_type == "embed":
                    texts = random.sample(self.sample_documents, 2)
                    response = await self.client.post(
                        f"{self.base_url}/embed",
                        json={
                            "texts": texts,
                            "store_in_vector_db": random.choice([True, False]),
                            "user_id": user["user_id"]
                        }
                    )
                
                request_count += 1
                
                if request_count % 10 == 0:
                    logger.info(f"Load simulation progress: {request_count} requests completed")
                
                # Random delay between requests
                await asyncio.sleep(random.uniform(0.5, 3.0))
                
            except Exception as e:
                logger.warning(f"Load simulation request failed: {e}")
                await asyncio.sleep(1)

    async def run_all_scenarios(self) -> None:
        """Run all demo scenarios in sequence."""
        logger.info("Starting AI Observability Demo Scenarios")
        
        # Check application health
        if not await self.health_check():
            logger.error("Application is not healthy, cannot run scenarios")
            return
        
        try:
            # Run scenarios in sequence
            await self.scenario_chat_completions()
            await asyncio.sleep(2)
            
            await self.scenario_embeddings_and_search()
            await asyncio.sleep(2)
            
            await self.scenario_local_inference()
            await asyncio.sleep(2)
            
            await self.scenario_full_pipeline()
            await asyncio.sleep(2)
            
            await self.scenario_error_conditions()
            await asyncio.sleep(2)
            
            logger.info("All demo scenarios completed successfully")
            
        except Exception as e:
            logger.error("Demo scenarios failed", error=str(e))

async def main():
    """Main entry point for demo scenarios."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Observability Demo Scenarios")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Base URL of the demo application")
    parser.add_argument("--scenario", choices=["all", "chat", "embed", "search", "local", "pipeline", "errors", "load"], 
                       default="all", help="Specific scenario to run")
    parser.add_argument("--load-duration", type=int, default=5, help="Load simulation duration in minutes")
    parser.add_argument("--iterations", type=int, default=1, help="Number of times to run the scenario")
    
    args = parser.parse_args()
    
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    demo = DemoScenarios(base_url=args.base_url)
    
    try:
        # Run the scenario for the specified number of iterations
        for iteration in range(args.iterations):
            if args.iterations > 1:
                logger.info(f"=== Starting iteration {iteration + 1}/{args.iterations} ===")
            
            if args.scenario == "all":
                await demo.run_all_scenarios()
            elif args.scenario == "chat":
                await demo.scenario_chat_completions()
            elif args.scenario == "embed":
                await demo.scenario_embeddings_and_search()
            elif args.scenario == "search":
                await demo.scenario_embeddings_and_search()
            elif args.scenario == "local":
                await demo.scenario_local_inference()
            elif args.scenario == "pipeline":
                await demo.scenario_full_pipeline()
            elif args.scenario == "errors":
                await demo.scenario_error_conditions()
            elif args.scenario == "load":
                await demo.scenario_load_simulation(duration_minutes=args.load_duration)
            
            if args.iterations > 1 and iteration < args.iterations - 1:
                logger.info(f"=== Completed iteration {iteration + 1}/{args.iterations}, waiting before next iteration ===")
                await asyncio.sleep(3)
    
    finally:
        # Close the HTTP client after all iterations are complete
        await demo.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())