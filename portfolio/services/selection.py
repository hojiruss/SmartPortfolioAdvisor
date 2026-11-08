from assessment.scoring import profile_for_score
from portfolio.models import Portfolio


def pick_portfolio(portfolio_set, risk_score):
    candidates = Portfolio.objects.filter(
        portfolio_set=portfolio_set,
        profile=profile_for_score(risk_score),
    )
    return min(candidates, key=lambda p: (abs(p.risk_score - risk_score), p.risk_score))