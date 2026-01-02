import sys


def start_server(port=8000):
    try:
        from meshchatx.meshchat import main

        sys.argv = [
            "meshchat",
            "--headless",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ]

        main()
    except Exception as e:
        print(f"Error starting MeshChatX server: {e}")
        import traceback

        traceback.print_exc()
        raise
