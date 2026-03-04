from providers.ollama_provider import ask_llm

def chat():

    print("AI Chat (type 'exit' to quit)")

    while True:

        q = input("AI> ")

        if q == "exit":
            break

        result = ask_llm(q, model="qwen2:1.5b")

        print(result)
