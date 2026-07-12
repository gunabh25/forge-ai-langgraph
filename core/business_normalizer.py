from typing import Dict, List, Any

CANONICAL_COMPONENTS = {
    "Claim Assessment": "Claim Evaluation",
    "Claim Validation": "Claim Evaluation",
    "Eligibility Check": "Claim Evaluation",
    "Eligibility Verification": "Claim Evaluation",

    "Document Upload": "Document Management",
    "Document Storage": "Document Management",

    "Payment Integration": "Payment Gateway",

    "Inventory Check": "Inventory Management",

    "Order Processing": "Order Management",
}

FORBIDDEN_COMPONENTS = {
    "Workflow Orchestration",
    "Workflow Engine",
    "Processing Engine",
    "Execution Engine",
    "Backend Service",
    "Portal Backend",
    "Microservice",
    "API Gateway",
    "Auth Service",
    "Controller",
    "Repository Service",
}


def normalize_components(components: List[str]) -> List[str]:
    normalized = []

    for component in components:
        name = component.strip()

        if name in FORBIDDEN_COMPONENTS:
            continue

        name = CANONICAL_COMPONENTS.get(name, name)

        if name not in normalized:
            normalized.append(name)

    return normalized


def normalize_plan(plan):
    print("\n========== BEFORE NORMALIZATION ==========")
    print(plan)

    if "major_components" in plan:
        plan["major_components"] = normalize_components(
            plan["major_components"]
        )

    print("\n========== AFTER NORMALIZATION ==========")
    print(plan)

    return plan