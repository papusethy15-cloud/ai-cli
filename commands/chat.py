from providers.ollama_provider import ask_llm
from config import CHAT_MODEL, CHAT_NUM_PREDICT

def chat():

    print("AI Chat (type 'exit' to quit)")

    while True:

        q = input("AI> ")

        if q == "exit":
            break

        # Chat uses a faster model and shorter outputs for better latency.
        result = ask_llm(
            q,
            model=CHAT_MODEL,
            options={"num_predict": CHAT_NUM_PREDICT},
        )

        print(result)
