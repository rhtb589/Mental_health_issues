from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from ml_ai.rag.retriever import retrieve
from ml_ai.longitudinal.classifier import classify

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "ml_ai" / "screening"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INSTRUMENTS = {
    "PHQ9": {
        "name": "PHQ-9 (Patient Health Questionnaire-9)",
        "purpose": "Screens for depression severity",
        "score_range": "0-27",
        "bands": [
            (0, 4, "Minimal depression"),
            (5, 9, "Mild depression"),
            (10, 14, "Moderate depression"),
            (15, 19, "Moderately severe depression"),
            (20, 27, "Severe depression"),
        ],
        "questions": [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself — or that you are a failure",
            "Trouble concentrating on things",
            "Moving or speaking too slowly, or being fidgety/restless",
            "Thoughts that you would be better off dead or of hurting yourself",
        ],
    },
    "GAD7": {
        "name": "GAD-7 (Generalized Anxiety Disorder-7)",
        "purpose": "Screens for generalized anxiety disorder",
        "score_range": "0-21",
        "bands": [
            (0, 4, "Minimal anxiety"),
            (5, 9, "Mild anxiety"),
            (10, 14, "Moderate anxiety"),
            (15, 21, "Severe anxiety"),
        ],
        "questions": [
            "Feeling nervous, anxious or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid as if something awful might happen",
        ],
    },
    "PHQ4": {
        "name": "PHQ-4 (Patient Health Questionnaire-4)",
        "purpose": "Brief ultra-brief screen for anxiety and depression",
        "score_range": "0-12",
        "bands": [
            (0, 2, "Minimal"),
            (3, 5, "Mild"),
            (6, 8, "Moderate"),
            (9, 12, "Severe"),
        ],
        "questions": [
            "Feeling nervous, anxious or on edge",
            "Not being able to stop or control worrying",
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
        ],
    },
    "SAFE-T": {
        "name": "SAFE-T / C-SSRS (Suicide Risk)",
        "purpose": "Evaluates suicidal ideation and risk",
        "score_range": "Structured (yes/no cascade)",
        "bands": [
            (0, 0, "No current suicidal ideation"),
            (1, 1, "Low-moderate risk: passive ideation"),
            (2, 2, "Moderate risk: active suicidal thoughts"),
            (3, 3, "Moderate risk: thoughts with method"),
            (4, 4, "High risk: suicidal ideation with intent"),
            (5, 5, "High risk: suicidal ideation with plan"),
        ],
        "questions": [
            "Wish to be dead",
            "Non-specific active suicidal thoughts",
            "Suicidal ideation with method (without plan)",
            "Suicidal ideation with some intent to act",
            "Suicidal ideation with specific plan and intent",
            "Suicidal behavior",
        ],
    },
}

INSTRUMENT_RECOMMENDATIONS = {
    "Depression": ["PHQ9", "PHQ4"],
    "Anxiety": ["GAD7", "PHQ4"],
    "Suicidal": ["SAFE-T", "PHQ9"],
    "Normal": ["PHQ4"],
}


def evaluate_screeners_for_conversation(conversation_text: str) -> dict:
    classification = classify(conversation_text)
    context = retrieve(conversation_text, n_results=2)
    recommended = INSTRUMENT_RECOMMENDATIONS.get(classification, ["PHQ4"])

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "conversation_text": conversation_text[:200],
        "baseline_classification": classification,
        "rag_context_snippet": context[:300],
        "recommended_instruments": [],
    }

    for inst_id in recommended:
        inst = INSTRUMENTS[inst_id]
        results["recommended_instruments"].append({
            "instrument_id": inst_id,
            "name": inst["name"],
            "purpose": inst["purpose"],
            "score_range": inst["score_range"],
            "severity_bands": [
                {"min": b[0], "max": b[1], "label": b[2]} for b in inst["bands"]
            ],
            "question_count": len(inst["questions"]),
        })

    return results


def run_evaluation():
    test_conversations = [
        "I have been feeling hopeless and worthless for weeks. Nothing interests me anymore.",
        "I cannot stop worrying about everything. My heart races and I feel restless.",
        "I want to end my life. I have been planning how to do it.",
        "I have been feeling down but it is not too bad. Just tired mostly.",
        "I feel anxious about work and cannot sleep at night.",
    ]

    all_results = []
    for text in test_conversations:
        result = evaluate_screeners_for_conversation(text)
        all_results.append(result)
        print(f"\nConversation: {text[:60]}...")
        print(f"Classification: {result['baseline_classification']}")
        print(f"Recommended: {[i['name'] for i in result['recommended_instruments']]}")

    output_path = OUTPUT_DIR / "screener_evaluation.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nEvaluation saved to {output_path}")
    return all_results


if __name__ == "__main__":
    run_evaluation()
