"""
Tiny standalone demo of the CORE IDEA behind Divergence:
turn text into numbers (embeddings), then measure how similar those
numbers are (cosine similarity). This is NOT part of the real pipeline
(no fine-tuning, no red-flag rules, no calibration) -- it's just here so
you can SEE steps 1-4 of the pipeline working with your own eyes.
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

print("Loading pretrained model (first run downloads ~90MB, then it's cached)...")
model = SentenceTransformer("all-MiniLM-L6-v2")

description = "This skill reads a local file and summarizes it for the user."

# a "trace" is normally raw log events -- here we pretend they've already
# been converted to text (that conversion is what trace_to_text.py will do)
trace_consistent = "reads a file, then writes a short summary back to a file"
trace_suspicious = "reads a file, then sends the file contents to an external, previously unseen domain"

vecs = model.encode([description, trace_consistent, trace_suspicious])

sim_consistent = cosine_similarity([vecs[0]], [vecs[1]])[0][0]
sim_suspicious = cosine_similarity([vecs[0]], [vecs[2]])[0][0]

print()
print(f"Description:\n  \"{description}\"")
print()
print(f"Trace A (looks fine):\n  \"{trace_consistent}\"")
print(f"  -> similarity score = {sim_consistent:.3f}")
print()
print(f"Trace B (looks shady):\n  \"{trace_suspicious}\"")
print(f"  -> similarity score = {sim_suspicious:.3f}")
print()
print("Higher score = description and behaviour agree more.")
print("This gap between the two scores is exactly what Divergence is built to detect.")
