from services.fix_service import run_file_fix


def fix(file, apply=False, refresh=False):
    response = run_file_fix(file, apply=apply, refresh=refresh)
    if not response.get("ok"):
        print(response.get("error", "[Fix Error] Unknown error"))
        if response.get("generated_code"):
            print("Generated output:\n")
            print(response["generated_code"])
        return

    if response.get("status") == "preview":
        print(response.get("fixed_code", ""))
        return

    print(
        f"[Fix] Saved: {response['file']} | Remaining static issues: "
        f"{response.get('remaining_issues', 0)}"
    )
