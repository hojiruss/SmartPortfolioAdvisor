from . import rules_config as rules

LOW_ABILITY_RULES = [
    (lambda t, l, e, i: t == 1, 'SHORT_TIME_HORIZON'),
    (lambda t, l, e, i: l == 1, 'HIGH_LIQUIDITY_NEED'),
    (lambda t, l, e, i: i == 1, 'HIGH_FINANCIAL_IMPACT'),
    (lambda t, l, e, i: e == 1 and l <= 1.5, 'LOW_RESOURCES_AND_HIGH_LIQUIDITY'),
]


def calculate_risk_ability(time_horizon, liquidity, external_resources, impact_of_loss):
    reason_code = [
        code
        for condition, code in LOW_ABILITY_RULES
        if condition(time_horizon, liquidity, external_resources, impact_of_loss)
    ]

    if reason_code:
        return 'LOW', reason_code

    if time_horizon == 3 and liquidity == 3 and external_resources == 3 and impact_of_loss == 3:
        return 'HIGH', ['ALL_ABILITY_FACTORS_STRONG']

    return 'MEDIUM', ['MIXED_ABILITY_FACTORS']

def calculate_knowledge_score(correct_answers_count):
    return rules.KNOWLEDGE_SCORE_MAP[correct_answers_count]

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

def detect_conflicts(tolerance, preference, composure, composure_source):
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

def run_assessment(answers):
    ability_level, ability_reasons = calculate_risk_ability(
        answers['time_horizon'],
        answers['liquidity'],
        answers['external_resources'],
        answers['impact_of_loss'],
    )

    knowledge_score = calculate_knowledge_score(answers['knowledge_correct_count'])

    perception_score, perception_reason = apply_perception_knowledge_guardrail(
        answers['risk_perception_raw'],
        knowledge_score,
    )

    composure_source = 'OBSERVED_PAST' if answers['has_loss_experience'] else 'HYPOTHETICAL'
    composure_score = answers['composure_score']
    past_behavior_confidence = answers.get('past_behavior_confidence') if composure_source == 'OBSERVED_PAST' else None

    behavioral_score = calculate_behavioral_score(
        answers['risk_tolerance'], answers['risk_preference'],
        knowledge_score, perception_score,
        answers['investing_experience'], composure_score,
    )

    behavioral_level = classify_behavioral_level(behavioral_score)
    behavioral_level, high_guardrail_reason = apply_behavioral_high_guardrail(
        behavioral_level, behavioral_score, answers['risk_tolerance'], answers['risk_preference'],
    )
    behavioral_level, low_confidence_reason = apply_low_confidence_guardrail(
        behavioral_level, composure_source, past_behavior_confidence,
    )

    severe_conflict, reversed_conflict = detect_conflicts(
        answers['risk_tolerance'], answers['risk_preference'], composure_score, composure_source,
    )

    reason_codes = ability_reasons + [r for r in [perception_reason, high_guardrail_reason, low_confidence_reason] if r]

    result = {
        'risk_ability_level': ability_level,
        'behavioral_score': behavioral_score,
        'behavioral_level': behavioral_level,
        'financial_knowledge_score': knowledge_score,
        'risk_perception_score': perception_score,
        'composure_source': composure_source,
        'past_behavior_confidence': past_behavior_confidence,
        'severe_behavioral_conflict': severe_conflict,
        'reverse_behavioral_conflict': reversed_conflict,
        'reason_codes': reason_codes,
    }

    if severe_conflict:
        result['status'] = 'AWAITING_CONFLICT_RESOLUTION'
        return result

    confidence = determine_assessment_confidence(severe_conflict, composure_source, past_behavior_confidence)
    result.update(finalize_assessment(ability_level, behavioral_level, confidence, severe_conflict= False, conflict_resolved= None))
    return result

def finalize_assessment(ability_level, behavioral_level, confidence, severe_conflict, conflict_resolved):
    base_level = reconcile_final_level(ability_level, behavioral_level)
    final_level, unresolved_reason = apply_unresolved_conflict_guardrail(base_level,
                                                                         severe_conflict,
                                                                         conflict_resolved)
    return {
        'assessment_confidence': confidence,
        'base_suitable_risk': base_level,
        'suitable_risk_level': final_level,
        'unresolved_reason': unresolved_reason,
        'status': 'COMPLETED',
    }

def resolved_conflict_and_finalize(ability_level, behavioral_level, conflict_outcome):
    confidence, conflict_resolved = resolve_conflict_confidence(conflict_outcome)
    result = finalize_assessment(ability_level, behavioral_level, confidence, severe_conflict=True, conflict_resolved=conflict_resolved)
    result['conflict_resolved'] = conflict_resolved
    return result

REQUIRED_NUMERIC_INPUTS = [
    'time_horizon', 'liquidity', 'external_resources', 'impact_of_loss',
    'risk_tolerance', 'risk_preference', 'risk_perception_raw',
    'investing_experience', 'composure_score',
]


def build_engine_input(choices_by_slot):
    has_loss = choices_by_slot['LOSS_EXPERIENCE'].outcome == rules.OUTCOME_HAS_LOSS

    if has_loss:
        composure_choice = choices_by_slot['COMPOSURE_ACTUAL']
    else:
        composure_choice = choices_by_slot['COMPOSURE_HYPOTHETICAL']

    knowledge_correct = sum(
        1 for slot in rules.KNOWLEDGE_SLOTS
        if choices_by_slot[slot].outcome == rules.OUTCOME_CORRECT
    )

    data = {
        'time_horizon': choices_by_slot['TIME_HORIZON'].value,
        'liquidity': choices_by_slot['LIQUIDITY'].value,
        'external_resources': choices_by_slot['EXTERNAL_RESOURCE'].value,
        'impact_of_loss': choices_by_slot['IMPACT_OF_LOSS'].value,
        'risk_tolerance': choices_by_slot['RISK_TOLERANCE'].value,
        'risk_preference': choices_by_slot['RISK_PREFERENCE'].value,
        'risk_perception_raw': choices_by_slot['RISK_PERCEPTION'].value,
        'investing_experience': choices_by_slot['INVESTING_EXPERIENCE'].value,
        'knowledge_correct_count': knowledge_correct,
        'has_loss_experience': has_loss,
        'composure_score': composure_choice.value,
    }

    if has_loss:
        data['past_behavior_confidence'] = choices_by_slot['PAST_RISK_AWARENESS'].outcome

    missing = [key for key in REQUIRED_NUMERIC_INPUTS if data[key] is None]
    if missing:
        raise ValueError(f'گزینه‌هایی بدون مقدار عددی: {missing}')

    if has_loss and data['past_behavior_confidence'] not in rules.VALID_AWARENESS_OUTCOMES:
        raise ValueError('برچسب آگاهی از ریسک گذشته نامعتبر است')

    return data


def build_assessment_fields(engine_input, result):
    reason_codes = list(result['reason_codes'])
    if result.get('unresolved_reason'):
        reason_codes.append(result['unresolved_reason'])

    return {
        'status': result['status'],
        'time_horizon_score': engine_input['time_horizon'],
        'liquidity_score': engine_input['liquidity'],
        'external_resources_score': engine_input['external_resources'],
        'impact_of_loss_score': engine_input['impact_of_loss'],
        'risk_tolerance_score': engine_input['risk_tolerance'],
        'risk_preference_score': engine_input['risk_preference'],
        'risk_perception_raw_score': engine_input['risk_perception_raw'],
        'risk_perception_score': result['risk_perception_score'],
        'knowledge_correct_answers': engine_input['knowledge_correct_count'],
        'financial_knowledge_score': result['financial_knowledge_score'],
        'investing_experience_score': engine_input['investing_experience'],
        'has_loss_experience': engine_input['has_loss_experience'],
        'risk_composure_score': engine_input['composure_score'],
        'composure_source': result['composure_source'],
        'past_behavior_confidence': result['past_behavior_confidence'],
        'severe_behavioral_conflict': result['severe_behavioral_conflict'],
        'reverse_behavioral_conflict': result['reverse_behavioral_conflict'],
        'risk_ability_level': result['risk_ability_level'],
        'behavioral_score': result['behavioral_score'],
        'behavioral_level': result['behavioral_level'],
        'assessment_confidence': result.get('assessment_confidence'),
        'base_suitable_risk': result.get('base_suitable_risk'),
        'suitable_risk_level': result.get('suitable_risk_level'),
        'reason_codes': reason_codes,
    }
