from . import rules_config as rules

LOW_ABILITY_RULES = [
    (lambda t, l, e, i: t == 1, 'SHORT_TIME_HORIZON'),
    (lambda t, l, e, i: l == 1, 'HIGH_LIQUIDITY_NEED'),
    (lambda t, l, e, i: i == 1, 'HIGH_FINANCIAL_IMPACT'),
    (lambda t, l, e, i: e == 1 and l <= 1.5, 'LOW_RESOURCES_AND_HIGH_LIQUIDITY'),
]


def calculate_risk_ability(time_horizon, liquidity, external_resource, impact_of_loss):
    reason_code = [
        code
        for condition, code in LOW_ABILITY_RULES
        if condition(time_horizon, liquidity, external_resource, impact_of_loss)
    ]

    if reason_code:
        return 'LOW', reason_code

    if time_horizon == 3 and liquidity == 3 and external_resource == 3 and impact_of_loss == 3:
        return 'HIGH', ['ALL_ABILITY_FACTORS_STRONG']

    return 'MEDIUM', ['MIXED_ABILITY_FACTORS']

def calculate_knowledge_score(correct_answers_count):
    return rules.KNOWLEDGE_SCORE_MAP(correct_answers_count)

def apply_perception_knowledge_guardrail(risk_perception_raw, financial_knowledge_score):
    if risk_perception_raw == 5 and financial_knowledge_score <= rules.LOW_KNOWLEDGE_THRESHOLD:
        return rules.RISK_PERCEPTION_MAX_WITH_LOW_KNOWLEDGE, 'RISK_PERCEPTION_KNOWLEDGE_CONFLICT'
    return risk_perception_raw, None

def calculate_behavioral_score(tolerance, preference, knowledge, perception, experience, composure):
    return tolerance + preference + knowledge + perception + experience + composure

def classify_behavioral_level(behavioral_score):
    if behavioral_score <= rules.BEHAVIORAL_LOW_MAX:
        return 'LOW'

    if behavioral_score <= rules.BEHAVIORAL_MEDIUM_MAX:
        return 'MEDIUM'

    return 'HIGH'

def apply_behavioral_high_guardrail(level, behavioral_score, tolerance, preference):
    if level != 'HIGH':
        return level, None

    if tolerance < rules.BEHAVIORAL_HIGH_MIN_TOLERANCE or preference < rules.BEHAVIORAL_HIGH_MIN_PREFERENCE:
        return 'MEDIUM', 'BEHAVIORAL_HIGH_GUARDRAIL'

    return level, None

def apply_low_confidence_guardrail(level, composure_source, past_behavior_confidence):
    if composure_source == 'OBSERVED_PAST' and past_behavior_confidence == 'LOW' and level == 'HIGH':
        return 'MEDIUM', 'LOW_CONFIDENCE_PAST_BEHAVIOR'
    return level, None

def detect_conflict(tolerance, preference, composure, composure_source):
    severe = False
    reverse = False

    if composure_source != 'OBSERVED_PAST':
        return severe, reverse

    if (
            tolerance >= rules.SEVERE_CONFLICT_TOLERANCE_MIN
            and preference >= rules.SEVERE_CONFLICT_PREFERENCE_MIN
            and composure <= rules.SEVERE_CONFLICT_COMPOSURE_MAX
    ):
        severe = True

    if (
            tolerance <= rules.REVERSE_CONFLICT_TOLERANCE_MAX
            and preference <= rules.REVERSE_CONFLICT_PREFERENCE_MAX
            and composure >= rules.REVERSE_CONFLICT_COMPOSURE_MIN
    ):
        reverse = True

    return severe, reverse

def determine_assessment_confidence(severe_conflict, composure_source, past_behavioral_confidence):
    if severe_conflict:
        return None

    if composure_source == 'HYPOTHETICAL':
        return 'LOW'

    return past_behavioral_confidence

def resolve_conflict_confidence(conflict_outcome):
    mapping = {
        'A': ('MEDIUM', True),
        'B': ('MEDIUM', True),
        'C': ('LOW', False),
        'D': ('LOW', False)
    }
    return mapping[conflict_outcome]

def reconcile_final_level(ability_level, behavioral_level):
    base = min(rules.RISK_LEVEL_ORDER[ability_level], rules.RISK_LEVEL_ORDER[behavioral_level])
    return rules.RISK_LEVEL_FROM_ORDER[base]

def apply_unresolved_conflict_guardrail(base_level, severe_conflict, conflict_resolved):
    if base_level == 'HIGH' and severe_conflict and conflict_resolved is False:
        return 'MEDIUM', 'UNRESOLVED_BEHAVIORAL_CONFLICT'

    return base_level, None

