from planexe_skill.shared.team import enrich


def run(ctx):
    enrich(ctx, "enrich_team_members_background_story.json", "enrich_team_members_environment_info_raw.json", "enrich_team_members_environment_info.json",
           {"equipment_needs": "equipment_needs", "facility_needs": "facility_needs"})
