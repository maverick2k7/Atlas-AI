from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

llm = ChatOllama(
    model="qwen2.5:7b-instruct-q4_K_M",
    base_url="http://localhost:11434",
    temperature=0.1,
)
response = llm.invoke([HumanMessage(content="Reply with one word: Working")])
print("Ollama response:", response.content)
print("PASS" if response.content else "FAIL")
