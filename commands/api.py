def serve_api():
    try:
        from api.server import run_server
    except RuntimeError as e:
        print(f"[API Error] {e}")
        return
    except Exception as e:
        print(f"[API Error] Failed to start API server: {e}")
        return

    run_server()
