"""Speed benchmark: measures tokens/sec with and without iGPU.

Run from backend/:
    .\\venv\\Scripts\\python.exe test_speed.py
"""
import time
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from config import settings

PROMPT = "Explain what RAG (Retrieval Augmented Generation) is in exactly 200 words."

print("=" * 60)
print("Atlas — Token Generation Speed Benchmark")
print(f"Model: {settings.ollama_model}")
print("=" * 60)

# Test 1: Supervisor-style (short output, 16 tokens max)
print("\n[Test 1] Routing decision (16-token max — supervisor style)")
llm_routing = ChatOllama(
    model=settings.ollama_model,
    base_url="http://localhost:11434",
    temperature=0.1,
    num_predict=16,
)
t0 = time.time()
resp = llm_routing.invoke([
    SystemMessage(content="You are a router. Reply with ONE word: researcher, writer, scheduler, or summariser."),
    HumanMessage(content="Schedule a meeting tomorrow at 3pm"),
])
elapsed = time.time() - t0
print(f"  Response  : {resp.content!r}")
print(f"  Time      : {elapsed:.2f}s")

# Test 2: Synthesis (longer output, 256 tokens)
print("\n[Test 2] Synthesis (256-token output — specialist agent style)")
llm_synth = ChatOllama(
    model=settings.ollama_model,
    base_url="http://localhost:11434",
    temperature=0.1,
    num_predict=256,
)
t0 = time.time()
resp2 = llm_synth.invoke([HumanMessage(content=PROMPT)])
elapsed2 = time.time() - t0
tokens = len(resp2.content.split())  # rough word count
tps = tokens / elapsed2
print(f"  Words out : ~{tokens}")
print(f"  Time      : {elapsed2:.2f}s")
print(f"  Speed     : ~{tps:.1f} words/sec  (~{tps*1.3:.1f} tok/s estimated)")
print(f"  Preview   : {resp2.content[:120]}...")

# Test 3: Streaming tokens (as the frontend sees it)
print("\n[Test 3] Streaming (256-token output, measuring TTFT + throughput)")
llm_stream = ChatOllama(
    model=settings.ollama_model,
    base_url="http://localhost:11434",
    temperature=0.1,
    num_predict=256,
    streaming=True,
)
t0 = time.time()
first_token_time = None
chunk_count = 0
full_text = ""
for chunk in llm_stream.stream([HumanMessage(content=PROMPT)]):
    if first_token_time is None:
        first_token_time = time.time() - t0
    chunk_count += 1
    full_text += chunk.content

total_time = time.time() - t0
words = len(full_text.split())
print(f"  TTFT      : {first_token_time:.2f}s  (time-to-first-token)")
print(f"  Total     : {total_time:.2f}s for ~{words} words")
print(f"  Speed     : ~{words/total_time:.1f} words/sec  (~{words*1.3/total_time:.1f} tok/s estimated)")
print(f"  Chunks    : {chunk_count}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Routing speed : {elapsed:.2f}s per decision")
print(f"  Synthesis TTFT: {first_token_time:.2f}s")
print(f"  Stream speed  : ~{words*1.3/total_time:.0f} tok/s")
if words*1.3/total_time > 20:
    print("  [FAST] iGPU acceleration is working!")
else:
    print("  [SLOW] Still running on CPU — iGPU not picking up model")
print("=" * 60)
