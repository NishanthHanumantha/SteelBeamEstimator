"""Quick Anthropic API connectivity check via centralized PromptExecutor."""

from src.llm.prompt_executor import PromptExecutor


def main() -> None:
    response = PromptExecutor().execute(
        user_prompt="Reply with exactly: API Working",
        system_prompt="Respond with plain text only.",
    )
    print(response)


if __name__ == "__main__":
    main()
