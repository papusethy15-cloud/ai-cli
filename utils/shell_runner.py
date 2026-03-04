import subprocess

def run_shell(command):

    print(f"[AI] running command: {command}")

    try:

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.stderr:
            print(result.stderr)

    except Exception as e:

        print(f"[AI] command failed: {e}")
