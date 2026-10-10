from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from . import services
from .models import Choice, RiskAssessment, UserAnswers
from .seed_data import seed_questionnaire

User = get_user_model()


# ===============================================================
# تست قواعد موتور (بدون دیتابیس)
# ===============================================================
def make_answers(**overrides):
    """یک کاربر قوی با تجربه‌ی افت واقعی: Ability = HIGH، Behavioral = HIGH (امتیاز 24)"""
    base = dict(
        time_horizon=3, liquidity=3, external_resources=3, impact_of_loss=3,
        risk_tolerance=4, risk_preference=4, risk_perception_raw=3,
        investing_experience=4, knowledge_correct_count=3,
        has_loss_experience=True, composure_score=5, past_behavior_confidence='HIGH',
    )
    base.update(overrides)
    return base


class RiskAbilityTests(SimpleTestCase):
    def test_all_strong_is_high(self):
        level, reasons = services.calculate_risk_ability(3, 3, 3, 3)
        self.assertEqual(level, 'HIGH')
        self.assertEqual(reasons, ['ALL_ABILITY_FACTORS_STRONG'])

    def test_short_horizon_is_low(self):
        level, reasons = services.calculate_risk_ability(1, 3, 3, 3)
        self.assertEqual(level, 'LOW')
        self.assertEqual(reasons, ['SHORT_TIME_HORIZON'])

    def test_high_liquidity_need_is_low(self):
        level, reasons = services.calculate_risk_ability(3, 1, 3, 3)
        self.assertEqual((level, reasons), ('LOW', ['HIGH_LIQUIDITY_NEED']))

    def test_high_financial_impact_is_low(self):
        level, reasons = services.calculate_risk_ability(3, 3, 3, 1)
        self.assertEqual((level, reasons), ('LOW', ['HIGH_FINANCIAL_IMPACT']))

    def test_low_resources_with_high_liquidity_need_is_low(self):
        level, reasons = services.calculate_risk_ability(3, 1.5, 1, 3)
        self.assertEqual((level, reasons), ('LOW', ['LOW_RESOURCES_AND_HIGH_LIQUIDITY']))

    def test_low_resources_alone_is_not_low(self):
        level, _ = services.calculate_risk_ability(3, 2.5, 1, 3)
        self.assertEqual(level, 'MEDIUM')

    def test_all_matching_reasons_are_recorded(self):
        level, reasons = services.calculate_risk_ability(1, 1, 1, 1)
        self.assertEqual(level, 'LOW')
        self.assertEqual(
            reasons,
            ['SHORT_TIME_HORIZON', 'HIGH_LIQUIDITY_NEED', 'HIGH_FINANCIAL_IMPACT',
             'LOW_RESOURCES_AND_HIGH_LIQUIDITY'],
        )

    def test_mixed_factors_is_medium(self):
        level, reasons = services.calculate_risk_ability(2, 3, 3, 3)
        self.assertEqual((level, reasons), ('MEDIUM', ['MIXED_ABILITY_FACTORS']))


class KnowledgeAndPerceptionTests(SimpleTestCase):
    def test_knowledge_mapping(self):
        self.assertEqual([services.calculate_knowledge_score(n) for n in range(4)], [1, 2, 3, 4])

    def test_perception_is_capped_when_knowledge_is_low(self):
        for knowledge in (1, 2):
            score, reason = services.apply_perception_knowledge_guardrail(5, knowledge)
            self.assertEqual(score, 3)
            self.assertEqual(reason, 'RISK_PERCEPTION_KNOWLEDGE_CONFLICT')

    def test_perception_is_kept_when_knowledge_is_enough(self):
        self.assertEqual(services.apply_perception_knowledge_guardrail(5, 3), (5, None))

    def test_perception_below_five_is_never_changed(self):
        self.assertEqual(services.apply_perception_knowledge_guardrail(4, 1), (4, None))


class BehavioralTests(SimpleTestCase):
    def test_level_boundaries(self):
        cases = {6: 'LOW', 13: 'LOW', 14: 'MEDIUM', 22: 'MEDIUM', 23: 'HIGH', 29: 'HIGH'}
        for score, expected in cases.items():
            self.assertEqual(services.classify_behavioral_level(score), expected, score)

    def test_high_requires_minimum_tolerance_and_preference(self):
        self.assertEqual(
            services.apply_behavioral_high_guardrail('HIGH', 26, 2, 5),
            ('MEDIUM', 'BEHAVIORAL_HIGH_GUARDRAIL'),
        )
        self.assertEqual(
            services.apply_behavioral_high_guardrail('HIGH', 26, 5, 2),
            ('MEDIUM', 'BEHAVIORAL_HIGH_GUARDRAIL'),
        )
        self.assertEqual(services.apply_behavioral_high_guardrail('HIGH', 26, 3, 3), ('HIGH', None))

    def test_guardrail_does_not_touch_other_levels(self):
        self.assertEqual(services.apply_behavioral_high_guardrail('MEDIUM', 15, 1, 1), ('MEDIUM', None))

    def test_low_confidence_past_behavior_blocks_high(self):
        self.assertEqual(
            services.apply_low_confidence_guardrail('HIGH', 'OBSERVED_PAST', 'LOW'),
            ('MEDIUM', 'LOW_CONFIDENCE_PAST_BEHAVIOR'),
        )
        self.assertEqual(services.apply_low_confidence_guardrail('HIGH', 'OBSERVED_PAST', 'HIGH'), ('HIGH', None))
        self.assertEqual(services.apply_low_confidence_guardrail('HIGH', 'HYPOTHETICAL', None), ('HIGH', None))


class ConflictTests(SimpleTestCase):
    def test_severe_conflict(self):
        self.assertEqual(services.detect_conflicts(4, 4, 2, 'OBSERVED_PAST'), (True, False))
        self.assertEqual(services.detect_conflicts(5, 5, 1, 'OBSERVED_PAST'), (True, False))

    def test_no_severe_conflict_when_any_condition_fails(self):
        self.assertEqual(services.detect_conflicts(3, 4, 1, 'OBSERVED_PAST'), (False, False))
        self.assertEqual(services.detect_conflicts(4, 4, 3, 'OBSERVED_PAST'), (False, False))

    def test_reverse_conflict(self):
        self.assertEqual(services.detect_conflicts(2, 2, 5, 'OBSERVED_PAST'), (False, True))

    def test_conflicts_are_ignored_for_hypothetical_behavior(self):
        self.assertEqual(services.detect_conflicts(5, 5, 1, 'HYPOTHETICAL'), (False, False))

    def test_conflict_answers(self):
        self.assertEqual(services.resolve_conflict_confidence('A'), ('MEDIUM', True))
        self.assertEqual(services.resolve_conflict_confidence('B'), ('MEDIUM', True))
        self.assertEqual(services.resolve_conflict_confidence('C'), ('LOW', False))
        self.assertEqual(services.resolve_conflict_confidence('D'), ('LOW', False))


class ReconciliationTests(SimpleTestCase):
    def test_edge_case_table_from_prd(self):
        cases = [
            ('LOW', 'HIGH', 'LOW'),
            ('HIGH', 'LOW', 'LOW'),
            ('MEDIUM', 'HIGH', 'MEDIUM'),
            ('HIGH', 'MEDIUM', 'MEDIUM'),
            ('HIGH', 'HIGH', 'HIGH'),
        ]
        for ability, behavioral, expected in cases:
            self.assertEqual(services.reconcile_final_level(ability, behavioral), expected)

    def test_unresolved_conflict_guardrail_only_affects_high(self):
        self.assertEqual(
            services.apply_unresolved_conflict_guardrail('HIGH', True, False),
            ('MEDIUM', 'UNRESOLVED_BEHAVIORAL_CONFLICT'),
        )
        self.assertEqual(services.apply_unresolved_conflict_guardrail('HIGH', True, True), ('HIGH', None))
        self.assertEqual(services.apply_unresolved_conflict_guardrail('MEDIUM', True, False), ('MEDIUM', None))
        self.assertEqual(services.apply_unresolved_conflict_guardrail('HIGH', False, None), ('HIGH', None))


class RunAssessmentScenarioTests(SimpleTestCase):
    def test_strong_user_gets_high(self):
        result = services.run_assessment(make_answers())
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['behavioral_score'], 24)
        self.assertEqual(result['suitable_risk_level'], 'HIGH')
        self.assertEqual(result['assessment_confidence'], 'HIGH')

    def test_short_horizon_user(self):
        result = services.run_assessment(make_answers(time_horizon=1))
        self.assertEqual(result['suitable_risk_level'], 'LOW')
        self.assertIn('SHORT_TIME_HORIZON', result['reason_codes'])

    def test_user_who_may_need_the_money(self):
        result = services.run_assessment(make_answers(liquidity=1))
        self.assertEqual(result['suitable_risk_level'], 'LOW')

    def test_user_with_low_capacity_to_recover(self):
        result = services.run_assessment(make_answers(impact_of_loss=1))
        self.assertEqual(result['suitable_risk_level'], 'LOW')

    def test_user_without_loss_experience_uses_hypothetical_and_low_confidence(self):
        result = services.run_assessment(make_answers(has_loss_experience=False, past_behavior_confidence=None))
        self.assertEqual(result['composure_source'], 'HYPOTHETICAL')
        self.assertEqual(result['assessment_confidence'], 'LOW')
        self.assertEqual(result['suitable_risk_level'], 'HIGH')

    def test_no_experience_is_not_penalised(self):
        with_experience = services.run_assessment(make_answers(has_loss_experience=False, investing_experience=1))
        self.assertEqual(with_experience['behavioral_score'], 24 - 3)

    def test_low_awareness_keeps_composure_but_blocks_high(self):
        result = services.run_assessment(make_answers(past_behavior_confidence='LOW'))
        self.assertEqual(result['behavioral_score'], 24)
        self.assertEqual(result['behavioral_level'], 'MEDIUM')
        self.assertIn('LOW_CONFIDENCE_PAST_BEHAVIOR', result['reason_codes'])
        self.assertEqual(result['assessment_confidence'], 'LOW')
        self.assertEqual(result['suitable_risk_level'], 'MEDIUM')

    def test_medium_awareness_gives_medium_confidence(self):
        result = services.run_assessment(make_answers(past_behavior_confidence='MEDIUM'))
        self.assertEqual(result['assessment_confidence'], 'MEDIUM')

    def severe_conflict_answers(self):
        # 4 + 4 + 4 + 5 + 5 + 1 = 23 → Behavioral HIGH، ولی ادعا و رفتار واقعی در تعارض‌اند
        return make_answers(risk_perception_raw=5, investing_experience=5, composure_score=1)

    def test_severe_conflict_waits_for_followup(self):
        result = services.run_assessment(self.severe_conflict_answers())
        self.assertEqual(result['status'], 'AWAITING_CONFLICT_RESOLUTION')
        self.assertTrue(result['severe_behavioral_conflict'])
        self.assertEqual(result['behavioral_level'], 'HIGH')
        self.assertNotIn('suitable_risk_level', result)

    def test_resolved_conflict_keeps_high_with_medium_confidence(self):
        result = services.resolved_conflict_and_finalize('HIGH', 'HIGH', 'A')
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(result['suitable_risk_level'], 'HIGH')
        self.assertEqual(result['assessment_confidence'], 'MEDIUM')
        self.assertTrue(result['conflict_resolved'])

    def test_unresolved_conflict_downgrades_high_to_medium(self):
        for answer in ('C', 'D'):
            result = services.resolved_conflict_and_finalize('HIGH', 'HIGH', answer)
            self.assertEqual(result['suitable_risk_level'], 'MEDIUM', answer)
            self.assertEqual(result['unresolved_reason'], 'UNRESOLVED_BEHAVIORAL_CONFLICT')
            self.assertEqual(result['assessment_confidence'], 'LOW')
            self.assertFalse(result['conflict_resolved'])

    def test_same_answers_always_give_same_result(self):
        first = services.run_assessment(make_answers())
        second = services.run_assessment(make_answers())
        self.assertEqual(first, second)


class EngineInputBuilderTests(SimpleTestCase):
    class FakeChoice:
        def __init__(self, value=None, outcome=''):
            self.value = value
            self.outcome = outcome

    def full_choices(self, has_loss=True):
        C = self.FakeChoice
        choices = {
            'TIME_HORIZON': C(3), 'LIQUIDITY': C(3), 'EXTERNAL_RESOURCE': C(3), 'IMPACT_OF_LOSS': C(3),
            'RISK_TOLERANCE': C(4), 'RISK_PREFERENCE': C(4), 'RISK_PERCEPTION': C(3),
            'INVESTING_EXPERIENCE': C(4),
            'KNOWLEDGE_1': C(outcome='CORRECT'), 'KNOWLEDGE_2': C(), 'KNOWLEDGE_3': C(outcome='CORRECT'),
            'LOSS_EXPERIENCE': C(outcome='HAS_LOSS_EXPERIENCE' if has_loss else 'NO_LOSS_EXPERIENCE'),
        }
        if has_loss:
            choices['COMPOSURE_ACTUAL'] = C(5)
            choices['PAST_RISK_AWARENESS'] = C(outcome='HIGH')
        else:
            choices['COMPOSURE_HYPOTHETICAL'] = C(3)
        return choices

    def test_counts_correct_knowledge_answers(self):
        data = services.build_engine_input(self.full_choices())
        self.assertEqual(data['knowledge_correct_count'], 2)

    def test_picks_actual_composure_when_loss_experienced(self):
        data = services.build_engine_input(self.full_choices(has_loss=True))
        self.assertEqual(data['composure_score'], 5)
        self.assertEqual(data['past_behavior_confidence'], 'HIGH')

    def test_picks_hypothetical_composure_without_loss_experience(self):
        data = services.build_engine_input(self.full_choices(has_loss=False))
        self.assertEqual(data['composure_score'], 3)
        self.assertNotIn('past_behavior_confidence', data)

    def test_missing_numeric_value_is_a_calculation_failure(self):
        choices = self.full_choices()
        choices['TIME_HORIZON'] = self.FakeChoice(value=None)
        with self.assertRaises(ValueError):
            services.build_engine_input(choices)


# ===============================================================
# تست API (با دیتابیس)
# ===============================================================
def pick(slot, value=None, outcome=None, wrong=False):
    queryset = Choice.objects.filter(question__slot=slot, question__is_active=True).order_by('order')
    if value is not None:
        return queryset.get(value=value)
    if outcome is not None:
        return queryset.filter(outcome=outcome).first()
    if wrong:
        return queryset.exclude(outcome='CORRECT').first()
    return queryset.first()


def strong_choices(**overrides):
    """هم‌ارز make_answers(): کاربر قوی با تجربه‌ی افت واقعی"""
    choices = {
        'INVESTMENT_GOAL': pick('INVESTMENT_GOAL'),
        'TIME_HORIZON': pick('TIME_HORIZON', value=3),
        'LIQUIDITY': pick('LIQUIDITY', value=3),
        'EXTERNAL_RESOURCE': pick('EXTERNAL_RESOURCE', value=3),
        'IMPACT_OF_LOSS': pick('IMPACT_OF_LOSS', value=3),
        'RISK_TOLERANCE': pick('RISK_TOLERANCE', value=4),
        'RISK_PREFERENCE': pick('RISK_PREFERENCE', value=4),
        'RISK_PERCEPTION': pick('RISK_PERCEPTION', value=3),
        'KNOWLEDGE_1': pick('KNOWLEDGE_1', outcome='CORRECT'),
        'KNOWLEDGE_2': pick('KNOWLEDGE_2', outcome='CORRECT'),
        'KNOWLEDGE_3': pick('KNOWLEDGE_3', outcome='CORRECT'),
        'INVESTING_EXPERIENCE': pick('INVESTING_EXPERIENCE', value=4),
        'LOSS_EXPERIENCE': pick('LOSS_EXPERIENCE', outcome='HAS_LOSS_EXPERIENCE'),
        'COMPOSURE_ACTUAL': pick('COMPOSURE_ACTUAL', value=5),
        'PAST_RISK_AWARENESS': pick('PAST_RISK_AWARENESS', outcome='HIGH'),
    }
    choices.update(overrides)
    return {slot: choice for slot, choice in choices.items() if choice is not None}


def to_payload(choices, amount='1000'):
    return {
        'investment_amount': amount,
        'answers': [{'question': c.question_id, 'choice': c.id} for c in choices.values()],
    }


class AssessmentApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        seed_questionnaire()
        cls.user = User.objects.create(email='user@example.com', username='user@example.com')
        cls.other_user = User.objects.create(email='other@example.com', username='other@example.com')

    def setUp(self):
        self.client.force_authenticate(self.user)

    def submit(self, choices=None, amount='1000'):
        choices = choices if choices is not None else strong_choices()
        return self.client.post('/api/assessment/submit/', to_payload(choices, amount), format='json')

    # ---------- پرسش‌نامه ----------
    def test_authentication_is_required(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/assessment/questions/').status_code, 401)
        self.assertEqual(self.client.post('/api/assessment/submit/', {}, format='json').status_code, 401)
        self.assertEqual(self.client.get('/api/assessment/result/').status_code, 401)

    def test_questions_list_hides_scores_and_correct_answers(self):
        response = self.client.get('/api/assessment/questions/')
        self.assertEqual(response.status_code, 200)
        slots = [question['slot'] for question in response.data]
        self.assertEqual(len(slots), 16)
        self.assertNotIn('CONFLICT_FOLLOWUP', slots)

        for question in response.data:
            for choice in question['choices']:
                self.assertNotIn('value', choice)
                if question['slot'] != 'LOSS_EXPERIENCE':
                    self.assertNotIn('outcome', choice)

        loss_question = next(q for q in response.data if q['slot'] == 'LOSS_EXPERIENCE')
        self.assertTrue(all('outcome' in choice for choice in loss_question['choices']))

    # ---------- ثبت موفق ----------
    def test_submit_strong_user_completes_and_stores_everything(self):
        response = self.submit()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'COMPLETED')
        self.assertEqual(response.data['suitable_risk_level'], 'HIGH')
        self.assertTrue(response.data['summary'])
        self.assertNotIn('behavioral_score', response.data)

        assessment = RiskAssessment.objects.get(pk=response.data['assessment_id'])
        self.assertEqual(assessment.user, self.user)
        self.assertEqual(assessment.behavioral_score, 24)
        self.assertEqual(assessment.risk_ability_level, 'HIGH')
        self.assertEqual(assessment.assessment_confidence, 'HIGH')
        self.assertEqual(assessment.questionnaire_version, 1)
        self.assertEqual(float(assessment.investment_amount), 1000.0)
        self.assertIsNotNone(assessment.completed_at)
        self.assertEqual(assessment.answers.count(), 15)

    def test_user_without_loss_experience(self):
        choices = strong_choices(LOSS_EXPERIENCE=pick('LOSS_EXPERIENCE', outcome='NO_LOSS_EXPERIENCE'))
        del choices['COMPOSURE_ACTUAL']
        del choices['PAST_RISK_AWARENESS']
        choices['COMPOSURE_HYPOTHETICAL'] = pick('COMPOSURE_HYPOTHETICAL', value=5)

        response = self.submit(choices)
        self.assertEqual(response.status_code, 200)
        assessment = RiskAssessment.objects.get(pk=response.data['assessment_id'])
        self.assertEqual(assessment.composure_source, 'HYPOTHETICAL')
        self.assertEqual(assessment.assessment_confidence, 'LOW')

    def test_short_horizon_limits_the_result(self):
        response = self.submit(strong_choices(TIME_HORIZON=pick('TIME_HORIZON', value=1)))
        self.assertEqual(response.data['suitable_risk_level'], 'LOW')
        self.assertIn('SHORT_TIME_HORIZON', response.data['reason_codes'])

    # ---------- اعتبارسنجی ----------
    def test_incomplete_assessment_is_rejected_and_not_saved(self):
        choices = strong_choices()
        del choices['RISK_TOLERANCE']
        response = self.submit(choices)
        self.assertEqual(response.status_code, 400)
        self.assertIn('RISK_TOLERANCE', response.data['missing_slots'])
        self.assertEqual(RiskAssessment.objects.count(), 0)

    def test_choice_from_another_question_is_rejected(self):
        payload = to_payload(strong_choices())
        payload['answers'][0]['choice'] = pick('TIME_HORIZON', value=3).id
        response = self.client.post('/api/assessment/submit/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(RiskAssessment.objects.count(), 0)

    def test_duplicate_answers_are_rejected(self):
        payload = to_payload(strong_choices())
        payload['answers'].append(payload['answers'][0])
        response = self.client.post('/api/assessment/submit/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_answers_for_both_branches_are_rejected(self):
        choices = strong_choices(COMPOSURE_HYPOTHETICAL=pick('COMPOSURE_HYPOTHETICAL', value=3))
        self.assertEqual(self.submit(choices).status_code, 400)

    def test_missing_branch_answers_are_rejected(self):
        choices = strong_choices()
        del choices['PAST_RISK_AWARENESS']
        self.assertEqual(self.submit(choices).status_code, 400)

    def test_conflict_question_cannot_be_sent_in_main_submit(self):
        choices = strong_choices(CONFLICT_FOLLOWUP=pick('CONFLICT_FOLLOWUP', outcome='A'))
        self.assertEqual(self.submit(choices).status_code, 400)

    def test_investment_amount_must_be_positive(self):
        for amount in ('0', '-5', 'abc'):
            self.assertEqual(self.submit(amount=amount).status_code, 400, amount)
        self.assertEqual(RiskAssessment.objects.count(), 0)

    # ---------- تعارض شدید ----------
    def conflict_choices(self):
        return strong_choices(
            RISK_PERCEPTION=pick('RISK_PERCEPTION', value=5),
            INVESTING_EXPERIENCE=pick('INVESTING_EXPERIENCE', value=5),
            COMPOSURE_ACTUAL=pick('COMPOSURE_ACTUAL', value=1),
        )

    def test_severe_conflict_flow_with_resolved_answer(self):
        response = self.submit(self.conflict_choices())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'AWAITING_CONFLICT_RESOLUTION')
        self.assertEqual(len(response.data['conflict_question']['choices']), 4)
        self.assertEqual(self.client.get('/api/assessment/result/').status_code, 404)

        assessment_id = response.data['assessment_id']
        answer = pick('CONFLICT_FOLLOWUP', outcome='A')
        resolved = self.client.post(
            f'/api/assessment/{assessment_id}/resolve-conflict/', {'choice': answer.id}, format='json'
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.data['status'], 'COMPLETED')
        self.assertEqual(resolved.data['suitable_risk_level'], 'HIGH')

        assessment = RiskAssessment.objects.get(pk=assessment_id)
        self.assertEqual(assessment.conflict_answer, 'A')
        self.assertTrue(assessment.conflict_resolved)
        self.assertEqual(assessment.assessment_confidence, 'MEDIUM')
        self.assertEqual(assessment.answers.count(), 16)

        again = self.client.post(
            f'/api/assessment/{assessment_id}/resolve-conflict/', {'choice': answer.id}, format='json'
        )
        self.assertEqual(again.status_code, 400)

    def test_severe_conflict_flow_with_unresolved_answer(self):
        assessment_id = self.submit(self.conflict_choices()).data['assessment_id']
        answer = pick('CONFLICT_FOLLOWUP', outcome='C')
        resolved = self.client.post(
            f'/api/assessment/{assessment_id}/resolve-conflict/', {'choice': answer.id}, format='json'
        )
        self.assertEqual(resolved.data['suitable_risk_level'], 'MEDIUM')
        self.assertIn('UNRESOLVED_BEHAVIORAL_CONFLICT', resolved.data['reason_codes'])

    def test_resolve_rejects_a_choice_from_another_question(self):
        assessment_id = self.submit(self.conflict_choices()).data['assessment_id']
        wrong = pick('TIME_HORIZON', value=3)
        response = self.client.post(
            f'/api/assessment/{assessment_id}/resolve-conflict/', {'choice': wrong.id}, format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_other_users_cannot_resolve_my_assessment(self):
        assessment_id = self.submit(self.conflict_choices()).data['assessment_id']
        self.client.force_authenticate(self.other_user)
        answer = pick('CONFLICT_FOLLOWUP', outcome='A')
        response = self.client.post(
            f'/api/assessment/{assessment_id}/resolve-conflict/', {'choice': answer.id}, format='json'
        )
        self.assertEqual(response.status_code, 404)

    def test_new_submit_abandons_a_pending_conflict_assessment(self):
        pending_id = self.submit(self.conflict_choices()).data['assessment_id']
        self.submit()
        self.assertEqual(RiskAssessment.objects.get(pk=pending_id).status, 'INCOMPLETE')

    # ---------- ارزیابی مجدد ----------
    def test_reassessment_keeps_previous_results(self):
        first = self.submit()
        second = self.submit(strong_choices(TIME_HORIZON=pick('TIME_HORIZON', value=1)))

        self.assertNotEqual(first.data['assessment_id'], second.data['assessment_id'])
        self.assertEqual(RiskAssessment.objects.filter(user=self.user, status='COMPLETED').count(), 2)

        latest = self.client.get('/api/assessment/result/')
        self.assertEqual(latest.data['assessment_id'], second.data['assessment_id'])
        self.assertEqual(latest.data['suitable_risk_level'], 'LOW')

        history = self.client.get('/api/assessment/history/')
        self.assertEqual([item['assessment_id'] for item in history.data],
                         [second.data['assessment_id'], first.data['assessment_id']])
        self.assertEqual(history.data[1]['suitable_risk_level'], 'HIGH')

    def test_users_only_see_their_own_results(self):
        self.submit()
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get('/api/assessment/result/').status_code, 404)
        self.assertEqual(self.client.get('/api/assessment/history/').data, [])

    def test_result_without_assessment_is_404(self):
        self.assertEqual(self.client.get('/api/assessment/result/').status_code, 404)

    # ---------- خطای محاسبه ----------
    def test_calculation_failure_saves_nothing(self):
        with mock.patch('assessment.views.services.run_assessment', side_effect=ValueError('boom')):
            with self.assertLogs('assessment.views', level='ERROR'):
                response = self.submit()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(RiskAssessment.objects.count(), 0)
        self.assertEqual(UserAnswers.objects.count(), 0)

    def test_misconfigured_choice_without_value_saves_nothing(self):
        choices = strong_choices()
        Choice.objects.filter(question__slot='TIME_HORIZON', value=3).update(value=None)
        with self.assertLogs('assessment.views', level='ERROR'):
            response = self.submit(choices)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(RiskAssessment.objects.count(), 0)

    # ---------- seed ----------
    def test_seed_is_idempotent(self):
        before = Choice.objects.count()
        self.assertEqual(seed_questionnaire(), 0)
        self.assertEqual(Choice.objects.count(), before)
