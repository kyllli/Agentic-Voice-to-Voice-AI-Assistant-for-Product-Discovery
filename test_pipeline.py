from assistant_graph import run_pipeline

query = "Recommend an eco-friendly stainless steel cleaner under $15"
result = run_pipeline(query)

print("\n=== FINAL ANSWER ===")
print(result["final_answer"])

print("\n=== CITATIONS ===")
print(result["citations"])
