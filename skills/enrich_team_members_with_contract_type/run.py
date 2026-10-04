from planexe_skill.shared.team import enrich


def run(ctx):
    enrich(ctx, "find_team_members.json", "enrich_team_members_contract_type_raw.json", "enrich_team_members_contract_type.json",
           {"contract_type": "contract_type", "contract_type_justification": "justification"})
