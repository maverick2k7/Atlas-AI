"""Test script for the ChromaDB memory layer.

Run from the backend/ directory:
    .\\venv\\Scripts\\python.exe test_memory.py
"""

import shutil
import os

# Clean up any previous test data so the test is idempotent
_test_db = os.path.join(os.path.dirname(__file__), "chroma_db")
if os.path.exists(_test_db):
    shutil.rmtree(_test_db)

from memory.chroma_store import save_memory, search_memory

print("=" * 50)
print("Atlas Memory Layer Test")
print("=" * 50)

# --- Save memories ---
print("\n[1] Saving memories...")
save_memory("The user prefers morning meetings", {"agent": "scheduler"})
print("    ✓ Saved: 'The user prefers morning meetings' (agent=scheduler)")

save_memory("User's professor is Dr. Ahmed", {"agent": "writer"})
print("    ✓ Saved: 'User\\'s professor is Dr. Ahmed' (agent=writer)")

# --- Search: broad query ---
print("\n[2] Searching: 'meeting preferences'")
results1 = search_memory("meeting preferences")
for r in results1:
    print(f"    → {r}")

# --- Search: filtered by agent ---
print("\n[3] Searching: 'professor' (filter_agent='writer')")
results2 = search_memory("professor", filter_agent="writer")
for r in results2:
    print(f"    → {r}")

# --- Verdict ---
print("\n" + "=" * 50)
if results1 and results2:
    print("PASS ✅  Both queries returned non-empty results.")
else:
    print("FAIL ❌  One or both queries returned empty results.")
    if not results1:
        print("    - 'meeting preferences' returned empty")
    if not results2:
        print("    - 'professor' (filter_agent=writer) returned empty")
print("=" * 50)
