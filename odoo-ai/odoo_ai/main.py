from __future__ import annotations


MODULE_QUESTIONS = [
    ("module_name", "Module name"),
    ("purpose", "What should this module do?"),
    ("users", "Who will use it?"),
    ("models", "What models are needed?"),
    ("dependencies", "Which Odoo dependencies are needed?"),
    ("views", "What views/screens are needed?"),
    ("security", "What security/access rules are needed?"),
    ("reports", "Any reports or exports?"),
    ("automation", "Any automation, scheduled jobs, or business rules?"),
]


def prompt(text: str) -> str:
    return input(f"{text}: ").strip()


def print_header(active_tab: str) -> None:
    print()
    print("🏨  Odoo AI  v0.1")
    print("  Standalone Terminal Project")
    print("────────────────────────────────────────────────────────────")
    print()
    tabs = ["Pipeline", "Agents", "Slave"]
    rendered = "   ".join(f"[{tab}]" if tab == active_tab else tab for tab in tabs)
    print(f"  {rendered}")
    print("  ────────────────────────────────────────────────────────")
    print()


def run_module_questionnaire() -> None:
    print()
    print("Module Builder")
    print("Answer the questions first. No code is generated before this is complete.")
    print()
    answers = {}
    for key, label in MODULE_QUESTIONS:
        answers[key] = prompt(label)

    print()
    print("Module brief")
    print("────────────────────────────────────────────────────────────")
    for key, label in MODULE_QUESTIONS:
        print(f"{label}: {answers.get(key, '')}")
    print()
    print("Next step: connect this brief to your code-generation backend.")
    print()


def pipeline_menu() -> None:
    while True:
        print_header("Pipeline")
        print("  1. Build something new")
        print("  2. Fix an error")
        print("  3. Review my code")
        print("  4. Generate full module")
        print("  5. Edit a file")
        print("  6. Add feature to module")
        print("  B. Back")
        print()
        choice = prompt("Choose an option").lower()
        if choice == "1" or choice == "4":
            run_module_questionnaire()
        elif choice in {"2", "3", "5", "6"}:
            print()
            print("Handler not wired yet in this standalone project.")
            print()
        elif choice == "b":
            return


def agents_menu() -> None:
    print_header("Agents")
    print("Agents area is not wired yet.")
    print()
    input("Press Enter to return...")


def slave_menu() -> None:
    print_header("Slave")
    run_module_questionnaire()
    input("Press Enter to return...")


def main() -> None:
    while True:
        print_header("Pipeline")
        print("  P. Pipeline")
        print("  A. Agents")
        print("  S. Slave")
        print("  Q. Quit")
        print()
        choice = prompt("Choose a tab").lower()
        if choice == "p":
            pipeline_menu()
        elif choice == "a":
            agents_menu()
        elif choice == "s":
            slave_menu()
        elif choice == "q":
            break


if __name__ == "__main__":
    main()
