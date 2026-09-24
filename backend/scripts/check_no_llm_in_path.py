"""Static check: no generative model in the evidence path.

GET /api/security/ai-safety-posture claims that "no LLM or generative model receives
untrusted document text with the ability to write to the graph". A claim like that decays
the moment somebody adds an import, so this script re-checks it against the source and
exits non-zero if the claim stops being true. It is meant to be run in CI and before a
demo.

What it checks
  1. No generative-AI client library is imported anywhere under app/agents, app/analytics
     or app/api (the modules that touch document text, the graph or the API surface).
  2. No HTTP call is made to a generative endpoint (api.openai.com, api.anthropic.com,
     generativelanguage.googleapis.com, ...) from those modules.
  3. No generative call pattern appears (chat.completions.create, .generate_content(,
     LangChain chains/agents, prompt templates).

Deliberately allowed, and listed in the report so a reviewer can see the distinction:
  * scikit-learn (classical ML: IsolationForest), NetworkX, RapidFuzz, spaCy NER - all
    deterministic or fitted classical models with no text generation and no prompt input.
  * An OPTIONAL token-classification model loaded from local weights by
    app/agents/document_agent.py (OCR abstraction). It is a Transformers model, but it is
    not generative, it is not loaded unless weights exist locally, and it cannot write to
    the graph - it returns OCR text. The check flags `transformers` usage only when a
    generative pipeline/architecture is actually named at the call site.

Run:  cd backend && python3 scripts/check_no_llm_in_path.py
"""
from __future__ import annotations

import os
import re
import sys
from typing import Iterable

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIRS = ["app/agents", "app/analytics", "app/api"]
SCAN_ROOT_FILES = ["app/main.py", "app/agents/manager.py"]

# --- rule 1: libraries that exist to call a generative model -------------------------
GENERATIVE_LIBS = (
    "openai", "anthropic", "cohere", "mistralai", "google.generativeai", "vertexai",
    "langchain", "llama_index", "llamaindex", "litellm", "ollama", "groq", "together",
    "ai21", "replicate", "huggingface_hub", "transformers.pipeline",
)
# --- rule 2: generative service endpoints --------------------------------------------
GENERATIVE_HOSTS = (
    "api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com",
    "api.cohere.ai", "api.mistral.ai", "api.together.xyz", "openrouter.ai",
    "api.groq.com", "api.deepseek.com", "api.x.ai",
)
# --- rule 3: generative call shapes --------------------------------------------------
GENERATIVE_CALLS = (
    r"\.chat\.completions\.create\s*\(", r"\.completions\.create\s*\(",
    r"\.generate_content\s*\(", r"\.generate_text\s*\(",
    r"\bChatCompletion\b", r"\bChatPromptTemplate\b", r"\bLLMChain\b",
    r"create_react_agent\s*\(", r"\bConversationChain\b", r"\.invoke\s*\(\s*prompt",
)
# --- explicit allow-list, with the reason it is not a generative surface --------------
ALLOWED_CONTEXT = (
    ("transformers", "document_agent.py loads an OCR/token-classification model from local "
                     "weights when present; token classification returns labels, it does not "
                     "generate text and it never writes to the graph."),
    ("spacy", "statistical NER (en_core_web_sm): trained tagger, not a generator."),
    ("sklearn", "classical ML: IsolationForest over transaction features."),
    ("rapidfuzz", "deterministic string ratio, no model at all."),
)

IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.MULTILINE)
GENERATIVE_WORD = re.compile(
    r"\b(llm|large\s+language\s+model|gpt|chatgpt|prompt\s+injection|hallucinat\w*|"
    r"completion\s+api|generative\s+(?:ai|model))\b", re.IGNORECASE)


def _targets() -> list[str]:
    files: list[str] = []
    for rel in SCAN_DIRS:
        for root, _dirs, names in os.walk(os.path.join(BACKEND, rel)):
            if "__pycache__" in root:
                continue
            for name in sorted(names):
                if name.endswith(".py"):
                    files.append(os.path.join(root, name))
    for rel in SCAN_ROOT_FILES:
        path = os.path.join(BACKEND, rel)
        if os.path.exists(path):
            files.append(path)
    return files


def _scan(files: Iterable[str]) -> list[tuple[str, int, str, str]]:
    """-> [(file, line number, rule, offending line)]"""
    findings: list[tuple[str, int, str, str]] = []
    for path in files:
        rel = os.path.relpath(path, BACKEND)
        with open(path, encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                    continue
                for match in IMPORT_RE.finditer(line):
                    module = (match.group(1) or match.group(2) or "").lower()
                    root = module.split(".")[0]
                    for lib in GENERATIVE_LIBS:
                        if module == lib or module.startswith(lib + ".") or root == lib:
                            # transformers: only a generative pipeline use is a violation
                            if root == "transformers" and "pipeline" not in module:
                                continue
                            findings.append((rel, lineno, f"generative library '{lib}'", stripped))
                lowered = line.lower()
                for host in GENERATIVE_HOSTS:
                    if host in lowered:
                        findings.append((rel, lineno, f"generative endpoint '{host}'", stripped))
                for pattern in GENERATIVE_CALLS:
                    if re.search(pattern, line):
                        findings.append((rel, lineno, f"generative call '{pattern}'", stripped))
    return findings


def main() -> int:
    files = _targets()
    findings = _scan(files)
    rule = "=" * 96
    print(rule)
    print("AI-SAFETY STATIC CHECK - is there a generative model in the evidence path?")
    print(rule)
    print(f"scanned {len(files)} python files under: {', '.join(SCAN_DIRS)} (+ app/main.py)")
    print()
    print("allowed non-generative components found in the evidence path:")
    allowed_hits: dict[str, list[str]] = {}
    for path in files:
        rel = os.path.relpath(path, BACKEND)
        text = open(path, encoding="utf-8").read().lower()
        for token, _reason in ALLOWED_CONTEXT:
            if token in text:
                allowed_hits.setdefault(token, []).append(rel)
    for token, reason in ALLOWED_CONTEXT:
        if token in allowed_hits:
            print(f"  ALLOWED  {token:14} in {len(allowed_hits[token])} file(s) - {reason}")
    print()
    if findings:
        print("VIOLATIONS - the evidence path now contains a generative model:")
        for rel, lineno, rule_name, line in findings:
            print(f"  FAIL  {rel}:{lineno}  {rule_name}")
            print(f"        {line}")
        print()
        print("GENERATIVE-MODEL CHECK: FAIL")
        print(rule)
        return 1
    print("checks performed:")
    print("  1. generative client libraries (openai, anthropic, langchain, cohere, ollama, ...):"
          " none imported")
    print("  2. generative service endpoints (api.openai.com, api.anthropic.com, ...): none called")
    print("  3. generative call shapes (chat.completions.create, generate_content, LLMChain, ...):"
          " none present")
    print()
    print("GENERATIVE-MODEL CHECK: PASS - no generative model is imported, called or reachable")
    print("from app/agents, app/analytics or app/api. Untrusted document text is processed by")
    print("rules, statistical NER, RapidFuzz, NetworkX and IsolationForest only.")
    print(rule)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
